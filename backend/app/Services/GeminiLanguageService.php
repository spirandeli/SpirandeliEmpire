<?php

namespace App\Services;

use App\Exceptions\GeminiApiException;
use App\Models\LanguageDailySession;
use App\Models\LanguageProfile;
use App\Models\User;
use App\Services\Gemini\GeminiClient;
use Illuminate\Support\Carbon;
use Illuminate\Support\Collection;
use Illuminate\Support\Facades\Log;

class GeminiLanguageService
{
    public const MODEL = 'gemini-3.8-flash';

    public function __construct(
        private readonly IntegrationService $integrationService,
    ) {
    }

    /**
     * Instancia o GeminiClient com a API Key do usuário configurada no cofre ou no .env.
     */
    private function getClient(User $user): GeminiClient
    {
        $apiKey = $this->integrationService->geminiApiKeyFor($user);

        if (empty($apiKey)) {
            throw new GeminiApiException('Chave da API do Google Gemini não configurada.');
        }

        return new GeminiClient(
            apiKey: $apiKey,
            model: self::MODEL,
            timeout: 90
        );
    }

    /**
     * Monta a instrução de sistema pedagógica injetando idioma e foco do usuário.
     */
    private function buildSystemInstruction(LanguageProfile $profile): array
    {
        $prompt = <<<PROMPT
# ROLE & OBJETIVO
Você é um Tutor Poliglota de Elite especialista em Aquisição Acelerada de Segunda Língua (SLA), Repetição Espaçada (SRS) e Micro-learning Executivo de 15 minutos, operando via modelo `gemini-3.8-flash`.

Seu objetivo é conduzir o usuário à fluência funcional no idioma {$profile->target_language} com foco em {$profile->learning_focus}, respeitando rigorosamente o limite cognitivo de 15 minutos diários.

# REGRAS PEDAGÓGICAS E DE FORMATO
1. Precisão de Nivelamento (CEFR):
   - No modo PLACEMENT_TEST, avalie vocabulário, gramática aplicada e compreensão contextual gradualmente (do A1 ao C1). Ao corrigir, identifique exatamente onde a curva de conhecimento do usuário quebra.
2. Engenharia dos 15 Minutos (Modo DAILY_LESSON):
   - Nunca gere exercícios longos ou cansativos. O conteúdo deve caber perfeitamente em 15 minutos:
     - Bloco 1 (3 min): 3 flashcards/questões rápidas resgatando termos da lista {{due_vocabulary_words}} (palavras que o usuário errou anteriormente).
     - Bloco 2 (6 min): Uma situação prática curta (máximo 120 palavras) conectada ao interesse do usuário ({$profile->learning_focus} — ex: negociação digital, e-commerce, tecnologia ou viagens) seguida de 3 desafios objetivos.
     - Bloco 3 (6 min): 1 Desafio de Produção Ativa onde o usuário deve escrever de 2 a 4 frases respondendo a um cenário real.
3. Correção Construtiva e Direta (Modo EVALUATE_SESSION):
   - Ao avaliar a resposta do usuário, nunca dê apenas "Certo" ou "Errado".
   - Entregue sempre em JSON estruturado:
     - is_correct: boolean
     - user_input: texto original
     - natural_native_version: como um nativo falaria na mesma situação
     - micro_explanation: explicação em português de no máximo 2 linhas
     - new_words_to_vault: array de palavras/expressões que o usuário errou ou aprendeu hoje para entrarem na fila de revisão espaçada.
4. Saída Estritamente em JSON:
   - Responda sempre respeitando o responseSchema solicitado pelo backend Laravel para renderização direta nos componentes do Vue 3.
PROMPT;

        return [
            'parts' => [
                ['text' => $prompt],
            ],
        ];
    }

    /**
     * Executa chamada segura ao Gemini registrando a auditoria em AiUsageLog.
     *
     * @return array<string, mixed>
     */
    private function callGemini(
        User $user,
        array $contents,
        array $systemInstruction,
        array $responseSchema,
        string $actionContext
    ): array {
        $client = $this->getClient($user);

        $generationConfig = [
            'temperature' => 0.2, // Baixa temperatura para precisão avaliativa e JSON determinístico
            'topP' => 0.95,
            'maxOutputTokens' => 4096,
            'responseMimeType' => 'application/json',
            'responseSchema' => $responseSchema,
        ];

        $startMs = microtime(true);
        $response = $client->generateContent(
            contents: $contents,
            systemInstruction: $systemInstruction,
            tools: null,
            generationConfig: $generationConfig
        );
        $latencyMs = (int) round((microtime(true) - $startMs) * 1000);

        // Extrai contagem de tokens da resposta oficial do Gemini
        $usageMeta = $response['usageMetadata'] ?? [];
        $promptTokens = (int) ($usageMeta['promptTokenCount'] ?? 250);
        $completionTokens = (int) ($usageMeta['candidatesTokenCount'] ?? 350);

        // Registra o consumo no medidor de IA e no FinOps Admin
        $user->recordAiUsage(
            promptTokens: $promptTokens,
            completionTokens: $completionTokens,
            model: self::MODEL,
            context: 'language_academy:' . $actionContext,
            latencyMs: $latencyMs
        );

        $candidateText = $response['candidates'][0]['content']['parts'][0]['text'] ?? '{}';
        $decoded = json_decode($candidateText, true);

        if (! is_array($decoded)) {
            Log::error('Resposta do Gemini 3.8 Flash não pôde ser decodificada como JSON', [
                'raw' => $candidateText,
            ]);
            throw new GeminiApiException('O Gemini 3.8 Flash retornou uma estrutura de dados inválida.');
        }

        return $decoded;
    }

    /**
     * 1. Gera o Teste de Nivelamento Diagnóstico Adaptativo (5 a 8 desafios graduais).
     */
    public function generatePlacementTest(LanguageProfile $profile): array
    {
        $systemInstruction = $this->buildSystemInstruction($profile);

        $prompt = <<<PROMPT
Gere um Teste de Nivelamento Diagnóstico Adaptativo para o idioma '{$profile->target_language}' com foco prático em '{$profile->learning_focus}'.
O teste deve conter de 6 a 8 desafios graduais, escalando do nível A1 (básico/saudação/vocabulário inicial) passando por A2, B1, B2 até C1 (nuances, expressões corporativas/avançadas).
Cada questão deve avaliar compreensão contextual, escolha vocabular ou estrutura frasal no contexto de {$profile->learning_focus}.
PROMPT;

        $schema = [
            'type' => 'OBJECT',
            'properties' => [
                'title' => ['type' => 'STRING'],
                'target_language' => ['type' => 'STRING'],
                'learning_focus' => ['type' => 'STRING'],
                'instructions' => ['type' => 'STRING'],
                'questions' => [
                    'type' => 'ARRAY',
                    'items' => [
                        'type' => 'OBJECT',
                        'properties' => [
                            'id' => ['type' => 'INTEGER'],
                            'target_cefr' => ['type' => 'STRING'], // A1, A2, B1, B2, C1
                            'type' => ['type' => 'STRING'], // multiple_choice
                            'question' => ['type' => 'STRING'],
                            'scenario' => ['type' => 'STRING'],
                            'options' => [
                                'type' => 'ARRAY',
                                'items' => ['type' => 'STRING'],
                            ],
                            'hint' => ['type' => 'STRING'],
                        ],
                        'required' => ['id', 'target_cefr', 'type', 'question', 'options'],
                    ],
                ],
            ],
            'required' => ['title', 'target_language', 'learning_focus', 'questions'],
        ];

        return $this->callGemini(
            user: $profile->user,
            contents: [['role' => 'user', 'parts' => [['text' => $prompt]]]],
            systemInstruction: $systemInstruction,
            responseSchema: $schema,
            actionContext: 'placement_test_generation'
        );
    }

    /**
     * 2. Avalia as respostas do Teste de Nivelamento e define o CEFR exato e os pontos cegos.
     */
    public function evaluatePlacementTest(
        LanguageProfile $profile,
        array $questions,
        array $userAnswers
    ): array {
        $systemInstruction = $this->buildSystemInstruction($profile);

        $evaluationPayload = [
            'questions' => $questions,
            'user_answers' => $userAnswers,
        ];

        $prompt = <<<PROMPT
Analise rigorosamente as respostas do usuário no Teste de Nivelamento Diagnóstico de {$profile->target_language} (foco: {$profile->learning_focus}).
Identifique exatamente onde a curva de proficiência do usuário falha.

Classifique o nível final estritamente no padrão CEFR oficial ('A1', 'A2', 'B1', 'B2', 'C1', 'C2').
Identifique os 'blind_spots' (pontos cegos/fraquezas críticas, ex: preposições em reuniões, tempos do passado, falsos cognatos).
Dados:
%s
PROMPT;

        $schema = [
            'type' => 'OBJECT',
            'properties' => [
                'cefr_level' => ['type' => 'STRING'], // A1, A2, B1, B2, C1, C2
                'score_percentage' => ['type' => 'INTEGER'],
                'executive_summary' => ['type' => 'STRING'],
                'strengths' => [
                    'type' => 'ARRAY',
                    'items' => ['type' => 'STRING'],
                ],
                'blind_spots' => [
                    'type' => 'ARRAY',
                    'items' => ['type' => 'STRING'],
                ],
                'recommended_study_plan' => ['type' => 'STRING'],
                'detailed_results' => [
                    'type' => 'ARRAY',
                    'items' => [
                        'type' => 'OBJECT',
                        'properties' => [
                            'question_id' => ['type' => 'INTEGER'],
                            'is_correct' => ['type' => 'BOOLEAN'],
                            'user_choice' => ['type' => 'STRING'],
                            'correct_answer' => ['type' => 'STRING'],
                            'explanation' => ['type' => 'STRING'],
                        ],
                        'required' => ['question_id', 'is_correct', 'explanation'],
                    ],
                ],
            ],
            'required' => ['cefr_level', 'score_percentage', 'executive_summary', 'blind_spots', 'detailed_results'],
        ];

        return $this->callGemini(
            user: $profile->user,
            contents: [['role' => 'user', 'parts' => [['text' => sprintf($prompt, json_encode($evaluationPayload, JSON_UNESCAPED_UNICODE))]]]],
            systemInstruction: $systemInstruction,
            responseSchema: $schema,
            actionContext: 'placement_test_evaluation'
        );
    }

    /**
     * 3. Prepara a Lição Diária de 15 Minutos nos 3 Blocos Dinâmicos.
     *
     * @param  LanguageProfile  $profile
     * @param  Collection<int, \App\Models\LanguageVocabularyVault>|array  $dueVocabulary
     * @return array<string, mixed>
     */
    public function generateDailyLesson(LanguageProfile $profile, $dueVocabulary = []): array
    {
        $systemInstruction = $this->buildSystemInstruction($profile);

        $vocabList = collect($dueVocabulary)->map(function ($item) {
            return is_array($item) ? $item['term_or_phrase'] : $item->term_or_phrase;
        })->take(5)->implode(', ');

        $blindSpotsList = ! empty($profile->weaknesses_diagnosis['blind_spots'])
            ? implode(', ', $profile->weaknesses_diagnosis['blind_spots'])
            : 'estruturas gerais e vocabulário chave';

        $prompt = <<<PROMPT
Gere a lição diária de 15 minutos (DAILY_LESSON) para o usuário.
- Idioma Alvo: {$profile->target_language}
- Foco Prático: {$profile->learning_focus}
- Nível CEFR Atual: {$profile->cefr_level}
- Termos Pendentes de Repetição Espaçada (SRS - Bloco 1): [{$vocabList}]
- Pontos Cegos a atacar: [{$blindSpotsList}]

ESTRUTURA OBRIGATÓRIA DOS 3 BLOCOS (15 MINUTOS):
- Bloco 1 (3 min - SRS): 3 flashcards/desafios rápidos resgatando palavras do vocabulário ou termos essenciais para o nível {$profile->cefr_level}.
- Bloco 2 (6 min - Imersão & Contexto): Um micro-diálogo ou situação de até 120 palavras conectada a '{$profile->learning_focus}', acompanhada de 3 perguntas de compreensão/interpretação objetivas.
- Bloco 3 (6 min - Produção Ativa): 1 desafio prático de escrita ativa onde o usuário deve formular 2 a 4 frases completas em '{$profile->target_language}' para responder a um cenário corporativo/real.
PROMPT;

        $schema = [
            'type' => 'OBJECT',
            'properties' => [
                'lesson_title' => ['type' => 'STRING'],
                'daily_theme' => ['type' => 'STRING'],
                'target_cefr' => ['type' => 'STRING'],
                'block1_srs' => [
                    'type' => 'OBJECT',
                    'properties' => [
                        'title' => ['type' => 'STRING'],
                        'duration_minutes' => ['type' => 'INTEGER'],
                        'instructions' => ['type' => 'STRING'],
                        'items' => [
                            'type' => 'ARRAY',
                            'items' => [
                                'type' => 'OBJECT',
                                'properties' => [
                                    'id' => ['type' => 'INTEGER'],
                                    'term' => ['type' => 'STRING'],
                                    'prompt' => ['type' => 'STRING'],
                                    'context_sentence' => ['type' => 'STRING'],
                                    'options' => [
                                        'type' => 'ARRAY',
                                        'items' => ['type' => 'STRING'],
                                    ],
                                    'correct_option_index' => ['type' => 'INTEGER'],
                                ],
                                'required' => ['id', 'term', 'prompt', 'options', 'correct_option_index'],
                            ],
                        ],
                    ],
                    'required' => ['title', 'duration_minutes', 'items'],
                ],
                'block2_immersion' => [
                    'type' => 'OBJECT',
                    'properties' => [
                        'title' => ['type' => 'STRING'],
                        'duration_minutes' => ['type' => 'INTEGER'],
                        'scenario_title' => ['type' => 'STRING'],
                        'scenario_text' => ['type' => 'STRING'],
                        'questions' => [
                            'type' => 'ARRAY',
                            'items' => [
                                'type' => 'OBJECT',
                                'properties' => [
                                    'id' => ['type' => 'INTEGER'],
                                    'question' => ['type' => 'STRING'],
                                    'options' => [
                                        'type' => 'ARRAY',
                                        'items' => ['type' => 'STRING'],
                                    ],
                                    'correct_option_index' => ['type' => 'INTEGER'],
                                ],
                                'required' => ['id', 'question', 'options', 'correct_option_index'],
                            ],
                        ],
                    ],
                    'required' => ['title', 'duration_minutes', 'scenario_title', 'scenario_text', 'questions'],
                ],
                'block3_active_output' => [
                    'type' => 'OBJECT',
                    'properties' => [
                        'title' => ['type' => 'STRING'],
                        'duration_minutes' => ['type' => 'INTEGER'],
                        'scenario_prompt' => ['type' => 'STRING'],
                        'required_elements' => [
                            'type' => 'ARRAY',
                            'items' => ['type' => 'STRING'],
                        ],
                        'example_starter' => ['type' => 'STRING'],
                    ],
                    'required' => ['title', 'duration_minutes', 'scenario_prompt', 'required_elements'],
                ],
            ],
            'required' => ['lesson_title', 'daily_theme', 'block1_srs', 'block2_immersion', 'block3_active_output'],
        ];

        return $this->callGemini(
            user: $profile->user,
            contents: [['role' => 'user', 'parts' => [['text' => $prompt]]]],
            systemInstruction: $systemInstruction,
            responseSchema: $schema,
            actionContext: 'daily_lesson_generation'
        );
    }

    /**
     * 4. Avalia as respostas da sessão diária (Modo EVALUATE_SESSION).
     */
    public function evaluateDailySession(
        LanguageProfile $profile,
        array $lessonPayload,
        array $userAnswers
    ): array {
        $systemInstruction = $this->buildSystemInstruction($profile);

        $payload = [
            'lesson' => $lessonPayload,
            'answers' => $userAnswers,
        ];

        $prompt = <<<PROMPT
Atue no modo EVALUATE_SESSION para a sessão de 15 minutos do usuário.
Analise as respostas dos 3 blocos, com atenção especial ao Bloco 3 (Produção Ativa):
- Nunca dê apenas 'Certo' ou 'Errado'.
- Para a produção ativa do usuário, forneça a versão natural como um nativo falaria na mesma situação corporativa/prática.
- Explicação em português de no máximo 2 linhas pontuando a nuance gramatical ou de etiqueta.
- Extraia novas palavras ou expressões chave ('new_words_to_vault') para que entrem automaticamente na fila de repetição espaçada do aluno.

DADOS DA SESSÃO:
%s
PROMPT;

        $schema = [
            'type' => 'OBJECT',
            'properties' => [
                'overall_score' => ['type' => 'INTEGER'], // 0 a 100
                'feedback_title' => ['type' => 'STRING'],
                'feedback_summary' => ['type' => 'STRING'],
                'block1_results' => [
                    'type' => 'ARRAY',
                    'items' => [
                        'type' => 'OBJECT',
                        'properties' => [
                            'item_id' => ['type' => 'INTEGER'],
                            'is_correct' => ['type' => 'BOOLEAN'],
                        ],
                        'required' => ['item_id', 'is_correct'],
                    ],
                ],
                'block2_results' => [
                    'type' => 'ARRAY',
                    'items' => [
                        'type' => 'OBJECT',
                        'properties' => [
                            'question_id' => ['type' => 'INTEGER'],
                            'is_correct' => ['type' => 'BOOLEAN'],
                        ],
                        'required' => ['question_id', 'is_correct'],
                    ],
                ],
                'block3_active_evaluation' => [
                    'type' => 'OBJECT',
                    'properties' => [
                        'is_correct' => ['type' => 'BOOLEAN'],
                        'user_input' => ['type' => 'STRING'],
                        'natural_native_version' => ['type' => 'STRING'],
                        'micro_explanation' => ['type' => 'STRING'],
                    ],
                    'required' => ['is_correct', 'user_input', 'natural_native_version', 'micro_explanation'],
                ],
                'new_words_to_vault' => [
                    'type' => 'ARRAY',
                    'items' => [
                        'type' => 'OBJECT',
                        'properties' => [
                            'term_or_phrase' => ['type' => 'STRING'],
                            'translation' => ['type' => 'STRING'],
                            'context_example' => ['type' => 'STRING'],
                        ],
                        'required' => ['term_or_phrase', 'translation'],
                    ],
                ],
            ],
            'required' => [
                'overall_score',
                'feedback_title',
                'feedback_summary',
                'block3_active_evaluation',
                'new_words_to_vault',
            ],
        ];

        return $this->callGemini(
            user: $profile->user,
            contents: [['role' => 'user', 'parts' => [['text' => sprintf($prompt, json_encode($payload, JSON_UNESCAPED_UNICODE))]]]],
            systemInstruction: $systemInstruction,
            responseSchema: $schema,
            actionContext: 'daily_session_evaluation'
        );
    }
}
