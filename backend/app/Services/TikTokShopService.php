<?php

namespace App\Services;

use App\Enums\LogLevel;
use App\Models\AgentLog;
use App\Models\ApprovalQueue;
use App\Models\Business;
use App\Models\ContentAsset;
use App\Models\Task;
use App\Models\TikTokProduct;
use App\Services\Gemini\GeminiClient;
use Illuminate\Support\Carbon;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Log;

class TikTokShopService
{
    public function __construct(
        private readonly IntegrationService $integrationService,
        private readonly ApprovalService $approvalService,
    ) {
    }

    /**
     * Minera produtos em alta para o nicho de um negócio, calculando métricas e scores.
     *
     * @param  Business  $business
     * @param  array<string, mixed>  $config  Parâmetros de mineração (min_commission, min_price, etc.)
     * @return array<int, TikTokProduct> Lista de produtos persistidos
     */
    public function mineTrendingProducts(Business $business, array $config = []): array
    {
        $minCommission = (float) ($config['min_commission_rate'] ?? 10.0);
        $minScore = (int) ($config['min_overall_score'] ?? 60);
        $maxItems = (int) ($config['max_items_per_run'] ?? 10);
        $niche = $business->niche ?? 'Geral';

        AgentLog::record(
            $business->user_id,
            'tiktok_mining_started',
            "Iniciando mineração de produtos em alta para o nicho \"{$niche}\".",
            LogLevel::Info,
            ['config' => $config],
            ['business_id' => $business->id]
        );

        // Capta produtos candidatos (via scraper/API feed simulado com dados analíticos realistas)
        $candidates = $this->fetchCandidateProductsFeed($niche, $config);

        $savedProducts = [];

        foreach ($candidates as $item) {
            $price = (float) $item['price'];
            $rate = (float) $item['commission_rate'];

            // Filtro de comissão mínima
            if ($rate < $minCommission) {
                continue;
            }

            $commValue = round($price * ($rate / 100), 2);

            $marginScore = (int) $item['margin_score'];
            $velocityScore = (int) $item['velocity_score'];
            $viralScore = (int) $item['viral_score'];

            $product = TikTokProduct::firstOrNew([
                'business_id' => $business->id,
                'external_id' => $item['external_id'],
            ]);

            $product->fill([
                'source' => $item['source'] ?? 'api',
                'title' => $item['title'],
                'category' => $item['category'] ?? $niche,
                'shop_name' => $item['shop_name'] ?? 'TikTok Shop Top Seller',
                'image_url' => $item['image_url'] ?? null,
                'product_url' => $item['product_url'] ?? null,
                'affiliate_link' => $item['affiliate_link'] ?? null,
                'price' => $price,
                'currency' => $item['currency'] ?? 'BRL',
                'commission_rate' => $rate,
                'commission_value' => $commValue,
                'sales_count' => (int) ($item['sales_count'] ?? 0),
                'sales_velocity' => (float) ($item['sales_velocity'] ?? 0),
                'rating' => (float) ($item['rating'] ?? 4.8),
                'reviews_count' => (int) ($item['reviews_count'] ?? 120),
                'margin_score' => $marginScore,
                'velocity_score' => $velocityScore,
                'viral_score' => $viralScore,
                'status' => TikTokProduct::STATUS_MINED,
                'raw_data' => $item,
                'mined_at' => now(),
            ]);

            $overallScore = $product->recalculateOverallScore();

            // Salva se atingir a nota de corte
            if ($overallScore >= $minScore) {
                $product->status = TikTokProduct::STATUS_SELECTED;
                $product->selected_at = now();
                $product->save();
                $savedProducts[] = $product;
            }

            if (count($savedProducts) >= $maxItems) {
                break;
            }
        }

        AgentLog::record(
            $business->user_id,
            'tiktok_mining_completed',
            "Mineração concluída: " . count($savedProducts) . " produto(s) qualificado(s) selecionado(s).",
            LogLevel::Success,
            ['selected_count' => count($savedProducts)],
            ['business_id' => $business->id]
        );

        return $savedProducts;
    }

    /**
     * Aciona o Gemini 3.8 para conceber a estratégia viral e o pacote completo de conteúdo de afiliado.
     *
     * @param  Business  $business
     * @param  TikTokProduct  $product
     * @return ApprovalQueue Entrega gerada e enviada para a fila de supervisão humana
     */
    public function generateAffiliateContentPackage(Business  $business, TikTokProduct $product): ApprovalQueue
    {
        $user = $business->user;

        AgentLog::record(
            $user->id,
            'content_generation_started',
            "Gerando estratégia e roteiro viral para \"{$product->title}\" com Gemini 3.8.",
            LogLevel::Info,
            ['product_id' => $product->id, 'overall_score' => $product->overall_score],
            ['business_id' => $business->id]
        );

        if (! $user->isAiActive()) {
            throw new \RuntimeException('Geração de conteúdo bloqueada pelo administrador (Kill-Switch ativo).');
        }

        if ($user->hasExceededMonthlyTokenLimit()) {
            throw new \RuntimeException('Limite mensal de tokens de IA atingido para o usuário.');
        }

        $apiKey = $this->integrationService->geminiApiKeyFor($user);
        $model = $this->integrationService->geminiModelFor($user) ?: config('services.gemini.model', 'gemini-3.8');

        $client = new GeminiClient(
            apiKey: $apiKey,
            model: $model,
            baseUrl: config('services.gemini.base_url')
        );

        $prompt = $this->buildContentGenerationPrompt($business, $product);

        $systemInstruction = [
            'parts' => [
                ['text' => 'Você é um Diretor Criativo e Especialista em Conteúdo Viral de Alta Conversão na TikTok Shop. Sua função é escrever roteiros magnéticos e pacotes completos de vendas de afiliados. Responda estritamente em formato JSON válido conforme solicitado.'],
            ],
        ];

        $generationConfig = [
            'temperature' => 0.4,
            'responseMimeType' => 'application/json',
        ];

        $response = $client->generateContent(
            contents: [
                [
                    'role' => 'user',
                    'parts' => [
                        ['text' => $prompt],
                    ],
                ],
            ],
            systemInstruction: $systemInstruction,
            generationConfig: $generationConfig
        );

        $usage = $response['usageMetadata'] ?? [];
        $promptTokens = (int) ($usage['promptTokenCount'] ?? 0);
        $completionTokens = (int) ($usage['candidatesTokenCount'] ?? 0);

        $user->recordAiUsage(
            promptTokens: $promptTokens,
            completionTokens: $completionTokens,
            model: $model,
            context: 'tiktok_content_generation',
            businessId: $business->id,
            latencyMs: 0
        );

        $rawText = $response['candidates'][0]['content']['parts'][0]['text'] ?? '{}';
        $data = json_decode($rawText, true) ?: [];

        // Salva a análise do produto atualizada
        if (! empty($data['ai_analysis'])) {
            $product->update([
                'ai_analysis' => $data['ai_analysis'],
                'status' => TikTokProduct::STATUS_CONTENT_READY,
            ]);
        }

        // Prepara o payload da entrega
        $packagePayload = [
            'product' => [
                'id' => $product->id,
                'external_id' => $product->external_id,
                'title' => $product->title,
                'price' => (float) $product->price,
                'commission_rate' => (float) $product->commission_rate,
                'commission_value' => (float) $product->commission_value,
                'overall_score' => $product->overall_score,
                'product_url' => $product->product_url,
                'affiliate_link' => $product->affiliate_link,
            ],
            'data_justification' => $data['data_justification'] ?? "Produto com alta taxa de conversão ({$product->commission_rate}% de comissão) e score geral de {$product->overall_score}/100.",
            'hooks' => $data['hooks'] ?? [
                'Pare de perder tempo com isso agora mesmo!',
                'O TikTok me fez comprar o produto mais útil do ano...',
                'Se você tem esse problema em casa, você precisa ver isso!',
            ],
            'selected_hook_index' => 0,
            'script' => $data['script'] ?? "Cena 1 (0-3s): Mostre o problema.\nCena 2 (3-8s): Demonstre a solução prática em ação.\nCena 3 (8-15s): Chame para a compra no link da bio.",
            'visual_prompts' => $data['visual_prompts'] ?? [
                'Close-up na embalagem e textura',
                'Demonstração prática de uso rápido em 4k',
                'Reação de surpresa ao ver o resultado',
            ],
            'caption' => $data['caption'] ?? "O achadinho que salvou a minha rotina! Link com desconto de frete grátis na bio ou no carrinho laranja.",
            'hashtags' => $data['hashtags'] ?? ['#tiktokshop', '#achadinhos', '#utilidades', '#dicas', '#compras'],
            'cta' => $data['cta'] ?? 'Clique no botão do produto abaixo antes que acabe o lote com desconto!',
            'target_audience' => $data['target_audience'] ?? 'Consumidores de compras por impulso e utilidades práticas',
            'suggested_posting_time' => $data['suggested_posting_time'] ?? '18:00',
        ];

        // Cria a tarefa de geração no Kanban para rastreabilidade
        $task = Task::create([
            'business_id' => $business->id,
            'user_id' => $user->id,
            'title' => "Gerar pacote de afiliado: {$product->title}",
            'description' => "Roteiro viral e 3 opções de hooks gerados automaticamente pelo Gemini 3.8.",
            'assignee' => 'agent',
            'status' => 'in_progress_agent',
            'priority' => 'high',
            'source' => 'agent',
            'agent_action' => 'generate_affiliate_content',
            'payload' => ['product_id' => $product->id],
        ]);

        // Submete para a Inbox de Supervisão
        $approval = $this->approvalService->submit(
            $business,
            [
                'title' => "Pacote TikTok Shop: {$product->title}",
                'summary' => "Comissão R$ {$product->commission_value} ({$product->commission_rate}%) | Score Geral: {$product->overall_score}/100",
                'type' => ApprovalQueue::TYPE_TIKTOK_CONTENT_PACKAGE,
                'payload' => $packagePayload,
                'priority' => $product->overall_score >= 80 ? 'urgent' : 'high',
                'agent_confidence' => 0.94,
                'task_id' => $task->id,
                'approvable_type' => 'tiktok_product',
                'approvable_id' => $product->id,
            ]
        );

        // Persiste os ContentAssets individuais versionados
        $this->persistContentAssets($business, $product, $approval, $packagePayload);

        AgentLog::record(
            $user->id,
            'content_package_ready',
            "Pacote de vídeo pronto e submetido para supervisão: \"{$product->title}\".",
            LogLevel::Success,
            ['approval_id' => $approval->id, 'hooks_count' => count($packagePayload['hooks'])],
            ['business_id' => $business->id, 'task_id' => $task->id]
        );

        return $approval;
    }

    /**
     * Processa a reescrita de uma seção específica quando solicitada pelo usuário no feedback.
     */
    public function revisePackageSection(ApprovalQueue $approval, string $feedback, ?string $section = null): ApprovalQueue
    {
        $this->approvalService->markRevising($approval);

        $business = $approval->business;
        $user = $business->user;
        $payload = $approval->payload;

        if (! $user->isAiActive()) {
            throw new \RuntimeException('Geração de conteúdo bloqueada pelo administrador (Kill-Switch ativo).');
        }

        if ($user->hasExceededMonthlyTokenLimit()) {
            throw new \RuntimeException('Limite mensal de tokens de IA atingido para o usuário.');
        }

        $apiKey = $this->integrationService->geminiApiKeyFor($user);
        $model = $this->integrationService->geminiModelFor($user) ?: config('services.gemini.model', 'gemini-3.8');

        $client = new GeminiClient(
            apiKey: $apiKey,
            model: $model,
            baseUrl: config('services.gemini.base_url')
        );

        $prompt = <<<PROMPT
Você recebeu um pedido de ajuste do usuário humano para aprimorar um pacote de vídeo de afiliado na TikTok Shop.
Seção solicitada: {$section}
Feedback do usuário: "{$feedback}"

Pacote atual:
{$this->jsonPretty($payload)}

Sua tarefa: Reescreva e melhore a seção indicada (ou todas se for o caso) atendendo estritamente ao feedback do usuário.
Retorne o JSON completo atualizado com a mesma estrutura.
PROMPT;

        $response = $client->generateContent(
            contents: [
                ['role' => 'user', 'parts' => [['text' => $prompt]]],
            ],
            systemInstruction: ['parts' => [['text' => 'Você é um Diretor de Conteúdo Viral especializado em ajustes rápidos e refinamento de roteiros. Responda estritamente em formato JSON válido.']]],
            generationConfig: ['temperature' => 0.4, 'responseMimeType' => 'application/json']
        );

        $usage = $response['usageMetadata'] ?? [];
        $promptTokens = (int) ($usage['promptTokenCount'] ?? 0);
        $completionTokens = (int) ($usage['candidatesTokenCount'] ?? 0);

        $user->recordAiUsage(
            promptTokens: $promptTokens,
            completionTokens: $completionTokens,
            model: $model,
            context: 'tiktok_approval_revision',
            businessId: $business->id,
            latencyMs: 0
        );

        $rawText = $response['candidates'][0]['content']['parts'][0]['text'] ?? '{}';
        $newPayload = json_decode($rawText, true) ?: $payload;

        // Se o JSON devolvido for válido, completa a revisão
        if (! empty($newPayload['hooks']) && ! empty($newPayload['script'])) {
            return $this->approvalService->completeRevision(
                $approval,
                $newPayload,
                "Ajuste realizado na seção [{$section}]: {$feedback}"
            );
        }

        // Fallback caso a API tenha retornado apenas a seção modificada
        if (! empty($newPayload[$section])) {
            $payload[$section] = $newPayload[$section];
            return $this->approvalService->completeRevision($approval, $payload, "Seção [{$section}] atualizada com sucesso.");
        }

        return $approval;
    }

    private function persistContentAssets(Business $business, TikTokProduct $product, ApprovalQueue $approval, array $payload): void
    {
        // 1. Hooks (3 opções)
        foreach ($payload['hooks'] as $idx => $hookText) {
            ContentAsset::create([
                'business_id' => $business->id,
                'tiktok_product_id' => $product->id,
                'approval_queue_id' => $approval->id,
                'type' => ContentAsset::TYPE_HOOK,
                'platform' => 'tiktok',
                'title' => "Hook Variação " . ($idx + 1),
                'body' => $hookText,
                'content' => ['index' => $idx, 'text' => $hookText],
                'is_selected' => $idx === ($payload['selected_hook_index'] ?? 0),
                'status' => 'pending_approval',
            ]);
        }

        // 2. Roteiro de vídeo cena a cena
        ContentAsset::create([
            'business_id' => $business->id,
            'tiktok_product_id' => $product->id,
            'approval_queue_id' => $approval->id,
            'type' => ContentAsset::TYPE_VIDEO_SCRIPT,
            'platform' => 'tiktok',
            'title' => "Roteiro Completo - {$product->title}",
            'body' => is_string($payload['script']) ? $payload['script'] : json_encode($payload['script'], JSON_UNESCAPED_UNICODE),
            'content' => ['script' => $payload['script']],
            'status' => 'pending_approval',
        ]);

        // 3. Prompts visuais
        ContentAsset::create([
            'business_id' => $business->id,
            'tiktok_product_id' => $product->id,
            'approval_queue_id' => $approval->id,
            'type' => ContentAsset::TYPE_VISUAL_PROMPT,
            'platform' => 'tiktok',
            'title' => 'Prompts de Cena e Gravação',
            'body' => implode("\n- ", (array) $payload['visual_prompts']),
            'content' => ['prompts' => $payload['visual_prompts']],
            'status' => 'pending_approval',
        ]);

        // 4. Caption e hashtags
        ContentAsset::create([
            'business_id' => $business->id,
            'tiktok_product_id' => $product->id,
            'approval_queue_id' => $approval->id,
            'type' => ContentAsset::TYPE_CAPTION,
            'platform' => 'tiktok',
            'title' => 'Legenda e Hashtags SEO',
            'body' => $payload['caption'] . "\n\n" . implode(' ', (array) $payload['hashtags']),
            'content' => ['caption' => $payload['caption'], 'hashtags' => $payload['hashtags']],
            'status' => 'pending_approval',
        ]);
    }

    private function buildContentGenerationPrompt(Business $business, TikTokProduct $product): string
    {
        $brandRules = $this->jsonPretty($business->brand_rules ?? []);

        return <<<PROMPT
Gere a estratégia viral e o pacote completo de afiliado da TikTok Shop para o seguinte produto vencedor minerado:

# DADOS DO PRODUTO:
- Nome: {$product->title}
- Categoria: {$product->category}
- Preço: R$ {$product->price}
- Taxa de Comissão: {$product->commission_rate}%
- Ganho Estimado por Venda: R$ {$product->commission_value}
- Velocidade de Vendas Recente: {$product->sales_velocity} vendas/dia
- Pontuações Calculadas: Margem={$product->margin_score}/100, Velocidade={$product->velocity_score}/100, Viralidade={$product->viral_score}/100, Geral={$product->overall_score}/100

# DIRETRIZES DA MARCA DO NEGÓCIO:
{$brandRules}

# REQUISITOS OBRIGATÓRIOS DO PACOTE (JSON):
Retorne um objeto JSON com as seguintes chaves estritas:
1. "data_justification": string explicando detalhadamente com dados por que este produto foi selecionado e o potencial de retorno.
2. "target_audience": string com o perfil do comprador ideal.
3. "hooks": array com exatamente 3 variações de hooks magnéticos para os primeiros 3 segundos (um focado em curiosidade/choque, um focado na dor imediata e um focado na demonstração visual).
4. "script": string com o roteiro completo segundo a segundo estruturado em formato (Tempo | Visual | Áudio/Fala).
5. "visual_prompts": array de strings com instruções claras de enquadramento de câmera, takes e planos para quem for gravar.
6. "caption": string persuasiva com gancho para o carrinho de compras.
7. "hashtags": array de 5 a 8 hashtags estratégicas de cauda longa e nicho.
8. "cta": string de chamada para ação direta e persuasiva.
9. "suggested_posting_time": string com melhor horário de postagem (ex: "18:00").
10. "ai_analysis": objeto com { core_pain_points: string[], hook_angles: string[], objections: string[], demonstration_ideas: string[] }.
PROMPT;
    }

    private function jsonPretty(mixed $data): string
    {
        return json_encode($data, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    }

    /**
     * Feed de dados analíticos simulados / integrados para captação de produtos em alta.
     */
    private function fetchCandidateProductsFeed(string $niche, array $config): array
    {
        $timestamp = time();

        return [
            [
                'external_id' => 'tt_' . md5($niche . '_1'),
                'title' => 'Mini Triturador Elétrico USB Recarregável',
                'category' => $niche,
                'shop_name' => 'Utilidades Prime',
                'price' => 49.90,
                'currency' => 'BRL',
                'commission_rate' => 20.00,
                'sales_count' => 1420,
                'sales_velocity' => 88.5,
                'rating' => 4.9,
                'reviews_count' => 312,
                'margin_score' => 85,
                'velocity_score' => 90,
                'viral_score' => 95,
                'product_url' => 'https://shop.tiktok.com/view/product/1001',
                'affiliate_link' => 'https://vt.tiktok.com/affiliate/abc1',
            ],
            [
                'external_id' => 'tt_' . md5($niche . '_2'),
                'title' => 'Dispenser Automático com Sensor Inteligente',
                'category' => $niche,
                'shop_name' => 'Casa Prática Oficial',
                'price' => 79.90,
                'currency' => 'BRL',
                'commission_rate' => 18.00,
                'sales_count' => 840,
                'sales_velocity' => 52.0,
                'rating' => 4.8,
                'reviews_count' => 195,
                'margin_score' => 78,
                'velocity_score' => 75,
                'viral_score' => 88,
                'product_url' => 'https://shop.tiktok.com/view/product/1002',
                'affiliate_link' => 'https://vt.tiktok.com/affiliate/abc2',
            ],
            [
                'external_id' => 'tt_' . md5($niche . '_3'),
                'title' => 'Removedor de Pelos e Fiapos Portátil Dupla Face',
                'category' => $niche,
                'shop_name' => 'Achadinhos Express',
                'price' => 29.90,
                'currency' => 'BRL',
                'commission_rate' => 25.00,
                'sales_count' => 2300,
                'sales_velocity' => 120.0,
                'rating' => 4.7,
                'reviews_count' => 450,
                'margin_score' => 90,
                'velocity_score' => 95,
                'viral_score' => 92,
                'product_url' => 'https://shop.tiktok.com/view/product/1003',
                'affiliate_link' => 'https://vt.tiktok.com/affiliate/abc3',
            ],
        ];
    }
}

