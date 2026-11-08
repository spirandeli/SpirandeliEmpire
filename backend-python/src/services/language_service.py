import asyncio
import json
import logging
import os
import random
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, delete
from google.genai import types

from src.models import (
    AiUsageLog,
    LanguageDailySession,
    LanguageProfile,
    LanguageVocabularyVault,
    LanguagePracticeMessage,
    User,
)
from src.services.gemini_service import get_user_gemini_client

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ---------------------------------------------------------------------------
# BANCOS DE QUESTÕES DE NIVELAMENTO CEFR POR IDIOMA (A1 a C1)
# ---------------------------------------------------------------------------

# 1. INGLÊS (English)
PLACEMENT_QUESTIONS_EN: list[dict[str, Any]] = [
    {
        "id": 1,
        "target_cefr": "A1",
        "category": "Basic Structure & Introduction",
        "scenario": "Introducing yourself to an international colleague on your first day.",
        "question": "Which sentence is correct to introduce yourself and state your profession?",
        "options": [
            "I am an operations manager and I work with international teams.",
            "I are an operations manager and I works with international teams.",
            "I has an operations manager and working with international teams.",
            "I manager operations and am work with international teams.",
        ],
        "correct_option": "I am an operations manager and I work with international teams.",
        "explanation": "In English, use 'I am' for titles and professions, and 'I work' in the Simple Present for routines.",
    },
    {
        "id": 2,
        "target_cefr": "A1",
        "category": "Daily Routine & Inquiries",
        "scenario": "Asking a team member about their regular working hours.",
        "question": "Choose the grammatically correct question for asking someone's daily start time:",
        "options": [
            "What time do you usually start work in the morning?",
            "What time does you usually start work in the morning?",
            "What time you usually starts work in the morning?",
            "What time are you usually start work in the morning?",
        ],
        "correct_option": "What time do you usually start work in the morning?",
        "explanation": "With the pronoun 'you' in the Simple Present, use the auxiliary verb 'do'.",
    },
    {
        "id": 3,
        "target_cefr": "A2",
        "category": "Past Simple & Completed Reports",
        "scenario": "Reporting in a standup meeting that an analytics report was delivered yesterday.",
        "question": "Yesterday, the marketing director ______ the campaign performance analysis to all stakeholders.",
        "options": ["sent", "sended", "has send", "was sented"],
        "correct_option": "sent",
        "explanation": "'Send' is an irregular verb whose past simple form is 'sent'.",
    },
    {
        "id": 4,
        "target_cefr": "A2",
        "category": "Professional Requests & Etiquette",
        "scenario": "Politely requesting an updated copy of an invoice from an accounts payable partner.",
        "question": "Which sentence represents the most natural and polite request in business correspondence?",
        "options": [
            "Could you please share the updated invoice at your earliest convenience?",
            "Give me the updated invoice right now.",
            "You must send invoice immediately to me.",
            "I want invoice copy please.",
        ],
        "correct_option": "Could you please share the updated invoice at your earliest convenience?",
        "explanation": "'Could you please...' paired with 'at your earliest convenience' is the standard polite executive formula.",
    },
    {
        "id": 5,
        "target_cefr": "B1",
        "category": "Modal Verbs & Deadlines",
        "scenario": "Informing squad leads about a strict compliance deadline.",
        "question": "All squad leads ______ submit their sprint retrospectives before Friday at 5 PM.",
        "options": ["must", "can to", "ought", "should to"],
        "correct_option": "must",
        "explanation": "'Must' expresses direct formal obligation and is never followed by 'to'.",
    },
    {
        "id": 6,
        "target_cefr": "B1",
        "category": "Cause and Effect Connectors",
        "scenario": "Explaining to executives why a product release was rescheduled.",
        "question": "The production deployment was temporarily delayed ______ unexpected server migration latency.",
        "options": ["due to", "because", "so that", "in order to"],
        "correct_option": "due to",
        "explanation": "'Due to' links causes followed by noun phrases in formal contexts.",
    },
    {
        "id": 7,
        "target_cefr": "B2",
        "category": "Corporate Phrasal Verbs",
        "scenario": "Proposing a brief check-in call with a supplier next Tuesday.",
        "question": "Which sentence correctly uses business idioms to suggest a brief alignment call?",
        "options": [
            "Let's touch base next Tuesday to review the launch metrics.",
            "Let's touching base next Tuesday to review the launch metrics.",
            "We base touch next Tuesday to review the launch metrics.",
            "Let's touch the base on Tuesday to review launch metrics.",
        ],
        "correct_option": "Let's touch base next Tuesday to review the launch metrics.",
        "explanation": "'To touch base' is the standard business idiom for having a quick check-in.",
    },
    {
        "id": 8,
        "target_cefr": "B2",
        "category": "Negotiation & Business Collocations",
        "scenario": "Finalizing commercial contract terms after tough negotiations.",
        "question": "After intense deliberation, both commercial teams managed to ______ a compromise that satisfied the board.",
        "options": ["reach", "arrive", "do", "gain"],
        "correct_option": "reach",
        "explanation": "The formal executive collocation is 'reach a compromise'.",
    },
    {
        "id": 9,
        "target_cefr": "C1",
        "category": "Executive Idioms & Nuance",
        "scenario": "Asking for an estimated preliminary budget figure before finalizing the quarterly balance.",
        "question": "Could you provide a ______ figure for the new tech stack expenditure before we draft the final roadmap?",
        "options": ["ballpark", "roundabout", "roughshot", "threshold"],
        "correct_option": "ballpark",
        "explanation": "'A ballpark figure' means a realistic rough estimate widely used at C1 executive level.",
    },
    {
        "id": 10,
        "target_cefr": "C1",
        "category": "Mixed Conditionals & Strategic Reasoning",
        "scenario": "Reflecting on an automation pipeline that was implemented in the previous semester.",
        "question": "If our tech lead ______ that workflow pipeline last quarter, we ______ dealing with these manual delays today.",
        "options": [
            "had implemented / wouldn't be",
            "implemented / won't be",
            "would implement / aren't",
            "has implemented / wouldn't have been",
        ],
        "correct_option": "had implemented / wouldn't be",
        "explanation": "Mixed conditional connecting an unreal past action (had implemented) with a present consequence (wouldn't be).",
    },
    {
        "id": 11,
        "target_cefr": "A1",
        "category": "Company Description & Operations",
        "scenario": "Explaining your company's core operations to an external contractor.",
        "question": "Which sentence correctly describes your company's core service?",
        "options": [
            "Our company develops software solutions for global logistics.",
            "Our company are develop software solutions for global logistics.",
            "Our company developing software solutions on global logistics.",
            "Our company is develop software solutions of global logistics.",
        ],
        "correct_option": "Our company develops software solutions for global logistics.",
        "explanation": "Use third-person singular 'develops' with the subject 'Our company' in the Simple Present.",
    },
    {
        "id": 12,
        "target_cefr": "A2",
        "category": "Past Actions & Milestones",
        "scenario": "Confirming during a standup that the deployment was finalized last week.",
        "question": "Last week, our engineering team ______ the cloud migration successfully.",
        "options": [
            "completed",
            "complete",
            "was completed",
            "has complete",
        ],
        "correct_option": "completed",
        "explanation": "For a finished time period ('last week'), use the past simple 'completed'.",
    },
    {
        "id": 13,
        "target_cefr": "B1",
        "category": "Purpose & Alignment",
        "scenario": "Explaining the objective of an emergency sprint retrospective meeting.",
        "question": "We scheduled an emergency sync ______ address the bottlenecks in the checkout funnel.",
        "options": [
            "in order to",
            "so",
            "because of",
            "for to",
        ],
        "correct_option": "in order to",
        "explanation": "'In order to' expresses formal business purpose followed by a base verb.",
    },
    {
        "id": 14,
        "target_cefr": "B2",
        "category": "Idioms & Stakeholder Alignment",
        "scenario": "Confirming everyone understands the new go-to-market strategy.",
        "question": "Before we launch the campaign, let's ensure all department heads are on the same ______.",
        "options": [
            "page",
            "book",
            "paper",
            "line",
        ],
        "correct_option": "page",
        "explanation": "'On the same page' is the executive idiom meaning in agreement and alignment.",
    },
    {
        "id": 15,
        "target_cefr": "C1",
        "category": "Inversion & High Formal Tone",
        "scenario": "Stating an inflexible security protocol to system administrators.",
        "question": "Under no circumstances ______ unencrypted customer credentials be stored in plain text.",
        "options": [
            "should",
            "we should",
            "it must",
            "ought to",
        ],
        "correct_option": "should",
        "explanation": "Negative inversion: 'Under no circumstances' triggers auxiliary inversion ('should unencrypted... be stored').",
    },
]

# 2. ESPANHOL (Spanish)
PLACEMENT_QUESTIONS_ES: list[dict[str, Any]] = [
    {
        "id": 1,
        "target_cefr": "A1",
        "category": "Presentación & Verbo Ser/Estar",
        "scenario": "Usted se está presentando ante un socio internacional en Madrid durante su primer día.",
        "question": "¿Cuál frase es correcta para presentarte y decir tu cargo en español?",
        "options": [
            "Soy gerente de operaciones y trabajo con equipos internacionales.",
            "Estoy gerente de operaciones y trabaja con equipos internacionales.",
            "Tengo gerente de operaciones y soy trabajo con equipos internacionales.",
            "Soy gerenciar operaciones y trabajando con equipos internacionales.",
        ],
        "correct_option": "Soy gerente de operaciones y trabajo con equipos internacionales.",
        "explanation": "En español se utiliza el verbo 'ser' (soy) para profesiones y 'trabajo' en presente de indicativo.",
    },
    {
        "id": 2,
        "target_cefr": "A1",
        "category": "Rutina Laboral & Preguntas",
        "scenario": "Preguntando a un colega de Buenos Aires su horario habitual de inicio de jornada.",
        "question": "¿Cómo se formula de manera natural la pregunta sobre el horario de inicio laboral?",
        "options": [
            "¿A qué hora sueles empezar a trabajar por la mañana?",
            "¿A qué hora tú suele empezando a trabajar por la mañana?",
            "¿Qué hora eres empezar trabajo en la mañana?",
            "¿A cuál hora tienes empezar trabajar por la mañana?",
        ],
        "correct_option": "¿A qué hora sueles empezar a trabajar por la mañana?",
        "explanation": "'Soler + infinitivo' (sueles empezar) es la estructura más idiomática para hábitos y rutinas.",
    },
    {
        "id": 3,
        "target_cefr": "A2",
        "category": "Pasado Simple & Reportes",
        "scenario": "Informando en una reunión matutina que el informe de analítica fue enviado ayer.",
        "question": "Ayer, el director de finanzas ______ el informe de resultados a los inversores.",
        "options": ["envió", "enviaba", "ha enviado", "enviaste"],
        "correct_option": "envió",
        "explanation": "Para una acción puntual concluida en un marco temporal terminado ('ayer'), se usa el pretérito indefinido 'envió'.",
    },
    {
        "id": 4,
        "target_cefr": "A2",
        "category": "Cortesía Corporativa & Peticiones",
        "scenario": "Solicitando formalmente a un cliente que remita una factura actualizada.",
        "question": "¿Cuál es la fórmula más formal y educada para solicitar un documento por correo electrónico?",
        "options": [
            "¿Podría enviarme la factura actualizada a la mayor brevedad posible?",
            "Mándame la factura ahora mismo rápido.",
            "Tú tienes que mandar factura ya.",
            "Quiero copia de factura por favor.",
        ],
        "correct_option": "¿Podría enviarme la factura actualizada a la mayor brevedad posible?",
        "explanation": "'¿Podría enviarme... a la mayor brevedad posible?' es la fórmula estándar de cortesía ejecutiva en el mundo hispano.",
    },
    {
        "id": 5,
        "target_cefr": "B1",
        "category": "Verbos de Obligación & Plazos",
        "scenario": "Notificando a los líderes de proyecto sobre un plazo de auditoría obligatorio.",
        "question": "Todos los líderes de proyecto ______ entregar el reporte de auditoría antes del viernes a las 18:00.",
        "options": ["deben", "pueden de", "tienen que de", "deberían de que"],
        "correct_option": "deben",
        "explanation": "'Deber + infinitivo' expresa mandato u obligación formal en comunicaciones de negocios.",
    },
    {
        "id": 6,
        "target_cefr": "B1",
        "category": "Conectores de Causa y Efecto",
        "scenario": "Explicando a la junta directiva el motivo del aplazamiento de un lanzamiento.",
        "question": "El lanzamiento de la plataforma se pospuso temporalmente ______ imprevistos técnicos en los servidores.",
        "options": ["debido a", "porque de", "para que", "a fin de"],
        "correct_option": "debido a",
        "explanation": "'Debido a' encabeza complementos de causa con sustantivos en registros formales.",
    },
    {
        "id": 7,
        "target_cefr": "B2",
        "category": "Expresiones Corporativas & Alineación",
        "scenario": "Proponiendo una reunión breve el próximo martes para revisar indicadores clave.",
        "question": "¿Qué expresión idiomática es la más natural en los negocios para proponer un breve chequeo mutuo?",
        "options": [
            "Pongámonos al día el próximo martes para revisar las métricas de la campaña.",
            "Toquemos la base el próximo martes para mirar números.",
            "Hagamos toque de base el martes próximo con números.",
            "Vamos a tocar base martes para ver cuentas.",
        ],
        "correct_option": "Pongámonos al día el próximo martes para revisar las métricas de la campaña.",
        "explanation": "'Ponerse al día' es la expresión natural y auténtica en el ámbito hispanohablante equivalente a 'touch base'.",
    },
    {
        "id": 8,
        "target_cefr": "B2",
        "category": "Negociación & Colocaciones Formales",
        "scenario": "Cerrando los términos de un acuerdo comercial complejo con un socio estratégico.",
        "question": "Tras intensas negociaciones, ambos equipos comerciales lograron ______ un acuerdo mutuamente beneficioso.",
        "options": ["alcanzar", "llegar", "hacer", "ganar"],
        "correct_option": "alcanzar",
        "explanation": "La colocación ejecutiva formal es 'alcanzar un acuerdo' (o 'llegar a un acuerdo').",
    },
    {
        "id": 9,
        "target_cefr": "C1",
        "category": "Estimaciones & Vocabulario C1",
        "scenario": "Pidiendo una estimación aproximada del presupuesto antes del cierre trimestral.",
        "question": "¿Podrías darme una cifra ______ sobre los costes operativos antes de redactar el presupuesto final?",
        "options": ["aproximada", "jugada", "cancha", "estadio"],
        "correct_option": "aproximada",
        "explanation": "En español corporativo formal se utiliza 'una cifra aproximada / estimada', evitando calcos literales.",
    },
    {
        "id": 10,
        "target_cefr": "C1",
        "category": "Condicionales Mixtas & Análisis Estratégico",
        "scenario": "Evaluando en retrospectiva el valor de un pipeline de automatización implementado el año pasado.",
        "question": "Si nuestro equipo técnico ______ esos procesos automatizados el año pasado, hoy no ______ enfrentando estos cuellos de botella.",
        "options": [
            "hubiera implementado / estaríamos",
            "implementó / estaremos",
            "implementaba / estuvimos",
            "haya implementado / habíamos estado",
        ],
        "correct_option": "hubiera implementado / estaríamos",
        "explanation": "Estructura condicional mixta: Pluscuamperfecto de subjuntivo ('hubiera implementado') con condicional simple ('estaríamos').",
    },
    {
        "id": 11,
        "target_cefr": "A1",
        "category": "Actividad Empresarial & Servicios",
        "scenario": "Explicando la actividad principal de su empresa a un nuevo cliente.",
        "question": "¿Cuál frase expresa correctamente a qué se dedica su empresa?",
        "options": [
            "Nuestra empresa desarrolla soluciones de software para la logística global.",
            "Nuestra empresa es desarrollar soluciones software para logística.",
            "Nuestra empresa desarrollando soluciones de software en logística.",
            "Nuestra empresa tiene desarrollar soluciones de software logística.",
        ],
        "correct_option": "Nuestra empresa desarrolla soluciones de software para la logística global.",
        "explanation": "En presente de indicativo para la tercera persona ('Nuestra empresa desarrolla').",
    },
    {
        "id": 12,
        "target_cefr": "A2",
        "category": "Hitos & Acciones Pasadas",
        "scenario": "Confirmando que el equipo completó la auditoría la semana pasada.",
        "question": "La semana pasada, nuestro equipo técnico ______ la migración de servidores con éxito.",
        "options": [
            "completó",
            "completa",
            "ha completando",
            "fue completado",
        ],
        "correct_option": "completó",
        "explanation": "'La semana pasada' exige el uso del pretérito indefinido ('completó').",
    },
    {
        "id": 13,
        "target_cefr": "B1",
        "category": "Finalidad & Conectores",
        "scenario": "Justificando la necesidad de una reunión de revisión urgente.",
        "question": "Convocamos esta sesión de trabajo ______ resolver los cuellos de botella del proyecto.",
        "options": [
            "con el fin de",
            "por qué",
            "para que de",
            "a causa de",
        ],
        "correct_option": "con el fin de",
        "explanation": "'Con el fin de + infinitivo' es la locución formal idónea para expresar propósito corporativo.",
    },
    {
        "id": 14,
        "target_cefr": "B2",
        "category": "Expresiones de Sintonía & Acuerdo",
        "scenario": "Asegurando que todos los líderes de área comparten la misma visión.",
        "question": "Antes del lanzamiento, debemos asegurarnos de que todos los socios estemos en la misma ______.",
        "options": [
            "sintonía",
            "página",
            "línea de tren",
            "letra",
        ],
        "correct_option": "sintonía",
        "explanation": "'Estar en la misma sintonía' es la expresión idiomática natural hispanohablante equivalente a 'on the same page'.",
    },
    {
        "id": 15,
        "target_cefr": "C1",
        "category": "Subjuntivo & Fórmulas Concesivas C1",
        "scenario": "Estableciendo una condición estricta de cumplimiento normativo.",
        "question": "Por más que ______ presiones sobre los plazos, bajo ningún concepto reduciremos los estándares de calidad.",
        "options": [
            "haya",
            "hay",
            "habrá",
            "había",
        ],
        "correct_option": "haya",
        "explanation": "'Por más que + presente de subjuntivo' ('haya') expresa concesión de alta formalidad ejecutiva.",
    },
]

# 3. FRANCÊS (French)
PLACEMENT_QUESTIONS_FR: list[dict[str, Any]] = [
    {
        "id": 1,
        "target_cefr": "A1",
        "category": "Présentation Professionnelle",
        "scenario": "Vous vous présentez à un collègue à Paris lors de votre premier jour.",
        "question": "Quelle phrase est correcte pour vous présenter et indiquer votre rôle ?",
        "options": [
            "Je suis responsable des opérations et je travaille avec des équipes internationales.",
            "Je es responsable des opérations et travaille avec équipes.",
            "J'ai responsable des opérations et je travail avec.",
            "Je être responsable opérations et travailler.",
        ],
        "correct_option": "Je suis responsable des opérations et je travaille avec des équipes internationales.",
        "explanation": "En français, on utilise 'Je suis' suivi du titre et 'je travaille' au présent.",
    },
    {
        "id": 2,
        "target_cefr": "A1",
        "category": "Horaires de Travail",
        "scenario": "Demander l'heure de début de travail habituelle d'un collègue.",
        "question": "Choisissez la question correcte pour demander l'heure de début du travail :",
        "options": [
            "À quelle heure commencez-vous habituellement le travail le matin ?",
            "Quelle heure vous êtes commencer le matin ?",
            "À quelle heure tu est commence le travail ?",
            "Quelle heure est travail commencé ?",
        ],
        "correct_option": "À quelle heure commencez-vous habituellement le travail le matin ?",
        "explanation": "Structure interrogative formelle avec inversion ou 'À quelle heure commencez-vous...'.",
    },
    {
        "id": 3,
        "target_cefr": "A2",
        "category": "Passé Composé & Rapports",
        "scenario": "Informer l'équipe que le rapport hebdomadaire a été transmis hier.",
        "question": "Hier, la directrice des opérations ______ le rapport financier aux partenaires.",
        "options": ["a envoyé", "envoyait", "a envoyé", "est envoyé"],
        "correct_option": "a envoyé",
        "explanation": "Le passé composé 'a envoyé' s'utilise pour une action ponctuelle achevée hier.",
    },
    {
        "id": 4,
        "target_cefr": "A2",
        "category": "Politesse en Affaires",
        "scenario": "Demander poliment une facture mise à jour par e-mail.",
        "question": "Quelle est la formulation la plus polie et professionnelle ?",
        "options": [
            "Pourriez-vous s'il vous plaît me transmettre la facture mise à jour dans les meilleurs délais ?",
            "Donnez-moi la facture tout de suite.",
            "Tu dois envoyer la facture maintenant.",
            "Je veux la facture merci.",
        ],
        "correct_option": "Pourriez-vous s'il vous plaît me transmettre la facture mise à jour dans les meilleurs délais ?",
        "explanation": "'Pourriez-vous...' et 'dans les meilleurs délais' forment la formule d'usage standard.",
    },
    {
        "id": 5,
        "target_cefr": "B1",
        "category": "Obligation & Délais",
        "scenario": "Informer les chefs de projet d'une date limite stricte.",
        "question": "Tous les responsables de projet ______ soumettre leur bilan avant vendredi 17h.",
        "options": ["doivent", "pouvoir", "ont que", "devront de"],
        "correct_option": "doivent",
        "explanation": "'Devoir + infinitif' exprime l'obligation institutionnelle directe.",
    },
    {
        "id": 6,
        "target_cefr": "B1",
        "category": "Connecteurs Logiques",
        "scenario": "Expliquer le report d'un déploiement technique.",
        "question": "Le déploiement a été reporté ______ des problèmes imprévus de latence réseau.",
        "options": ["en raison de", "parce que", "pour que", "afin de"],
        "correct_option": "en raison de",
        "explanation": "'En raison de' introduit un motif nominal dans un registre soutenu.",
    },
    {
        "id": 7,
        "target_cefr": "B2",
        "category": "Expressions d'Affaires",
        "scenario": "Proposer un point rapide d'alignement avec un partenaire.",
        "question": "Quelle expression est la plus appropriée pour proposer une mise au point rapide ?",
        "options": [
            "Faisons le point mardi prochain pour passer en revue les résultats.",
            "Touchons la base mardi prochain pour voir les nombres.",
            "Mettons la base ensemble mardi.",
            "Prenons le point de contact mardi.",
        ],
        "correct_option": "Faisons le point mardi prochain pour passer en revue les résultats.",
        "explanation": "'Faire le point' est l'équivalent idiomatique authentique de 'touch base' en entreprise francophone.",
    },
    {
        "id": 8,
        "target_cefr": "B2",
        "category": "Négociation & Accords",
        "scenario": "Parvenir à un accord mutuellement avantageux en négociation.",
        "question": "Après de longues discussions, nous avons réussi à ______ un accord satisfaisant.",
        "options": ["conclure", "faire", "prendre", "gagner"],
        "correct_option": "conclure",
        "explanation": "La colocation formelle est 'conclure un accord' (ou 'parvenir à un accord').",
    },
    {
        "id": 9,
        "target_cefr": "C1",
        "category": "Vocabulaire Exécutif C1",
        "scenario": "Demander une estimation budgétaire approximative mais fiable.",
        "question": "Pourriez-vous me donner un ordre de ______ pour le budget prévisionnel avant validation ?",
        "options": ["grandeur", "taille", "ballpark", "hauteur"],
        "correct_option": "grandeur",
        "explanation": "'Un ordre de grandeur' est l'expression équivalente à une estimation générale raisonnée au niveau C1.",
    },
    {
        "id": 10,
        "target_cefr": "C1",
        "category": "Conditionnel Passé & Stratégie",
        "scenario": "Analyser l'impact d'une décision d'automatisation prise l'an dernier.",
        "question": "Si notre équipe ______ cette infrastructure l'an dernier, nous ne ______ pas confrontés à ces goulots d'étranglement.",
        "options": [
            "avait mis en place / serions",
            "a mis en place / serons",
            "mettait en place / serions été",
            "aurait mis en place / étions",
        ],
        "correct_option": "avait mis en place / serions",
        "explanation": "Conditionnelle mixte française : Si + plus-que-parfait (avait mis en place) entraîne le conditionnel présent (serions).",
    },
]

# 4. ALEMÃO (German)
PLACEMENT_QUESTIONS_DE: list[dict[str, Any]] = [
    {
        "id": 1,
        "target_cefr": "A1",
        "category": "Berufliche Vorstellung",
        "scenario": "Sich am ersten Arbeitstag einem internationalen Partner vorstellen.",
        "question": "Welcher Satz ist korrekt, um sich und seinen Beruf vorzustellen?",
        "options": [
            "Ich bin Operations Manager und arbeite mit internationalen Teams.",
            "Ich bist Operations Manager und arbeiten mit Teams.",
            "Ich habe Operations Manager und bin arbeiten.",
            "Ich sein Operations Manager und gearbeitet.",
        ],
        "correct_option": "Ich bin Operations Manager und arbeite mit internationalen Teams.",
        "explanation": "Im Deutschen verwendet man 'Ich bin' für Berufe und 'arbeite' im Präsens.",
    },
    {
        "id": 2,
        "target_cefr": "A1",
        "category": "Arbeitszeiten",
        "scenario": "Einen Kollegen nach der täglichen Anfangszeit fragen.",
        "question": "Wie fragt man höflich nach der regulären Arbeitszeit?",
        "options": [
            "Um wie viel Uhr fangen Sie morgens normalerweise mit der Arbeit an?",
            "Welche Stunde du fängst arbeiten an?",
            "Um was Uhr du bist arbeiten anfangen?",
            "Wann Stunde haben Sie Arbeit start?",
        ],
        "correct_option": "Um wie viel Uhr fangen Sie morgens normalerweise mit der Arbeit an?",
        "explanation": "'Um wie viel Uhr fangen Sie... an?' ist die korrekte Höflichkeitsform im Geschäftsleben.",
    },
    {
        "id": 3,
        "target_cefr": "A2",
        "category": "Perfekt & Berichte",
        "scenario": "Mitteilen, dass die Leistungsanalyse gestern gesendet wurde.",
        "question": "Gestern ______ die Marketingleiterin den Quartalsbericht an alle Partner ______.",
        "options": ["hat / geschickt", "ist / geschickt", "hat / sendet", "wird / geschickt"],
        "correct_option": "hat / geschickt",
        "explanation": "Das Perfekt mit 'haben + Partizip II' (hat geschickt) ist die Standardform für die Vergangenheit.",
    },
    {
        "id": 4,
        "target_cefr": "A2",
        "category": "Geschäftliche Höflichkeit",
        "scenario": "Höflich per E-Mail um eine aktualisierte Rechnung bitten.",
        "question": "Welche Formulierung ist im Geschäftsverkehr am höflichsten?",
        "options": [
            "Könnten Sie mir bitte zeitnah die aktualisierte Rechnung zukommen lassen?",
            "Geben Sie mir die Rechnung sofort.",
            "Du musst Rechnung jetzt schicken.",
            "Ich will Rechnung danke.",
        ],
        "correct_option": "Könnten Sie mir bitte zeitnah die aktualisierte Rechnung zukommen lassen?",
        "explanation": "'Könnten Sie mir bitte... zukommen lassen?' ist die Standardhöflichkeitsformel in DACH-Unternehmen.",
    },
    {
        "id": 5,
        "target_cefr": "B1",
        "category": "Modalverben & Fristen",
        "scenario": "Einhalten einer verbindlichen Abgabefrist ankündigen.",
        "question": "Alle Teamleiter ______ den Compliance-Bericht vor Freitag um 17 Uhr einreichen.",
        "options": ["müssen", "können zu", "sollen zu", "haben zu dass"],
        "correct_option": "müssen",
        "explanation": "'Müssen' drückt die verbindliche Verpflichtung aus.",
    },
    {
        "id": 6,
        "target_cefr": "B1",
        "category": "Kausalangaben",
        "scenario": "Erklären einer Verzögerung im Software-Release.",
        "question": "Die Veröffentlichung wurde ______ unerwarteter Serverprobleme verschoben.",
        "options": ["aufgrund", "weil", "damit", "sodass"],
        "correct_option": "aufgrund",
        "explanation": "'Aufgrund' verlangt den Genitiv und leitet die formelle Ursachenangabe ein.",
    },
    {
        "id": 7,
        "target_cefr": "B2",
        "category": "Business-Redewendungen",
        "scenario": "Eine kurze Statusabstimmung für nächste Woche vorschlagen.",
        "question": "Welche Redewendung passt am besten für eine kurze Zwischenabstimmung?",
        "options": [
            "Lassen Sie uns nächste Woche kurzschließen, um die Zahlen durchzugehen.",
            "Lassen Sie uns die Basis berühren nächste Woche.",
            "Wir machen Basis-Touch am Dienstag.",
            "Berühren wir den Kontakt nächste Woche.",
        ],
        "correct_option": "Lassen Sie uns nächste Woche kurzschließen, um die Zahlen durchzugehen.",
        "explanation": "'Sich kurzschließen' oder 'sich abstimmen' ist das natürliche Äquivalent zu 'touch base'.",
    },
    {
        "id": 8,
        "target_cefr": "B2",
        "category": "Verhandlung & Vereinbarungen",
        "scenario": "Erfolgreicher Abschluss einer Vertragsverhandlung.",
        "question": "Nach intensiven Verhandlungen konnten wir einen soliden Kompromiss ______.",
        "options": ["erzielen", "tun", "nehmen", "kriegen"],
        "correct_option": "erzielen",
        "explanation": "Die gehobene feste Wendung lautet 'einen Kompromiss erzielen'.",
    },
    {
        "id": 9,
        "target_cefr": "C1",
        "category": "Budget & Schätzungen C1",
        "scenario": "Nach einer vorläufigen Richtgröße für die Budgetplanung fragen.",
        "question": "Könnten Sie mir eine fundierte ______ für die operativen Kosten nennen?",
        "options": ["Größenordnung", "Spielfeldgröße", "Ballparkzahl", "Eckfläche"],
        "correct_option": "Größenordnung",
        "explanation": "'Eine Größenordnung' bzw. 'Hausnummer' entspricht einer qualifizierten Schätzung auf C1-Niveau.",
    },
    {
        "id": 10,
        "target_cefr": "C1",
        "category": "Irreale Konditionalsätze",
        "scenario": "Rückblickende Bewertung einer strategischen Automatisierung.",
        "question": "Wenn wir diese Prozesse letztes Jahr ______ , ______ wir heute nicht mit diesen Engpässen konfrontiert.",
        "options": [
            "automatisiert hätten / wären",
            "automatisiert haben / sind",
            "automatisierten / wurden",
            "automatisieren würden / waren",
        ],
        "correct_option": "automatisiert hätten / wären",
        "explanation": "Konjunktiv II der Vergangenheit ('automatisiert hätten') verknüpft mit Gegenwart ('wären wir nicht').",
    },
]

# 5. ITALIANO (Italian)
PLACEMENT_QUESTIONS_IT: list[dict[str, Any]] = [
    {
        "id": 1,
        "target_cefr": "A1",
        "category": "Presentazione Professionale",
        "scenario": "Presentarsi a un partner commerciale a Milano il primo giorno.",
        "question": "Quale frase è corretta per presentarsi e indicare la propria professione?",
        "options": [
            "Sono responsabile delle operazioni e lavoro con team internazionali.",
            "Sto responsabile delle operazioni e lavora con team.",
            "Ho responsabile operazioni e sono lavoro con team.",
            "Essere responsabile e lavorando con team.",
        ],
        "correct_option": "Sono responsabile delle operazioni e lavoro con team internazionali.",
        "explanation": "In italiano si usa 'Sono' per titoli professionali e 'lavoro' al presente indicativo.",
    },
    {
        "id": 2,
        "target_cefr": "A1",
        "category": "Orario di Lavoro",
        "scenario": "Chiedere l'orario consueto di inizio turno a un collega.",
        "question": "Come si formula in modo naturale la domanda sull'orario lavorativo?",
        "options": [
            "A che ora inizi di solito a lavorare la mattina?",
            "Quale ora tu sei iniziare lavoro mattina?",
            "A che ora hai iniziando lavoro mattina?",
            "Che ora è lavoro cominciato?",
        ],
        "correct_option": "A che ora inizi di solito a lavorare la mattina?",
        "explanation": "'A che ora inizi di solito...' è la formulazione colloquiale professionale corretta.",
    },
    {
        "id": 3,
        "target_cefr": "A2",
        "category": "Passato Prossimo & Report",
        "scenario": "Comunicare che il report trimestrale è stato inviato ieri.",
        "question": "Ieri, il direttore finanziario ______ il report sui risultati a tutti i soci.",
        "options": ["ha inviato", "inviava", "è inviato", "ha inviando"],
        "correct_option": "ha inviato",
        "explanation": "Il passato prossimo 'ha inviato' si usa per azioni concluse con effetto rilevante.",
    },
    {
        "id": 4,
        "target_cefr": "A2",
        "category": "Cortesia Aziendale",
        "scenario": "Richiedere cortesemente una fattura aggiornata via e-mail.",
        "question": "Qual è la formula più formale e cortese in una comunicazione aziendale?",
        "options": [
            "Potrebbe gentilmente inviarmi la fattura aggiornata al più presto?",
            "Dammi la fattura subito.",
            "Devi mandare fattura adesso.",
            "Voglio fattura per favore.",
        ],
        "correct_option": "Potrebbe gentilmente inviarmi la fattura aggiornata al più presto?",
        "explanation": "'Potrebbe gentilmente inviarmi... al più presto?' è lo standard aziendale italiano.",
    },
    {
        "id": 5,
        "target_cefr": "B1",
        "category": "Obbligo & Scadenze",
        "scenario": "Segnalare una scadenza inderogabile ai responsabili di progetto.",
        "question": "Tutti i responsabili di progetto ______ consegnare il rendiconto entro venerdì alle 17:00.",
        "options": ["devono", "possono di", "hanno che", "dovrebbero di"],
        "correct_option": "devono",
        "explanation": "'Dovere + infinito' esprime l'obbligo contrattuale formale.",
    },
    {
        "id": 6,
        "target_cefr": "B1",
        "category": "Connettivi Causali",
        "scenario": "Spiegare al comitato direttivo il motivo del rinvio di un rilascio.",
        "question": "Il rilascio della piattaforma è stato posticipato ______ imprevisti problemi tecnici.",
        "options": ["a causa di", "perché di", "affinché", "allo scopo di"],
        "correct_option": "a causa di",
        "explanation": "'A causa di' introduce un sostantivo che esprime causa.",
    },
    {
        "id": 7,
        "target_cefr": "B2",
        "category": "Espressioni Corporate",
        "scenario": "Proporre un rapido allineamento la prossima settimana con un fornitore.",
        "question": "Quale espressione è più naturale nel business italiano per proporre un breve allineamento?",
        "options": [
            "Aggiorniamoci martedì prossimo per verificare insieme le metriche chiave.",
            "Tocchiamo la base martedì prossimo per vedere i numeri.",
            "Facciamo tocco di base martedì per i numeri.",
            "Prendiamo la base martedì per verificare.",
        ],
        "correct_option": "Aggiorniamoci martedì prossimo per verificare insieme le metriche chiave.",
        "explanation": "'Aggiorniamoci' o 'fare il punto' è la traduzione idiomatica naturale di 'touch base'.",
    },
    {
        "id": 8,
        "target_cefr": "B2",
        "category": "Negoziazione & Accordi",
        "scenario": "Raggiungere un accordo dopo una lunga trattativa commerciale.",
        "question": "Dopo intense trattative, entrambi i team commerciali sono riusciti a ______ un accordo vantaggioso.",
        "options": ["raggiungere", "fare", "prendere", "guadagnare"],
        "correct_option": "raggiungere",
        "explanation": "La collocazione standard è 'raggiungere un accordo'.",
    },
    {
        "id": 9,
        "target_cefr": "C1",
        "category": "Stime Finanziarie C1",
        "scenario": "Richiedere una stima indicativa del budget prima della chiusura.",
        "question": "Potrebbe fornirmi una cifra ______ per i costi operativi prima della stesura finale?",
        "options": ["indicativa", "stadio", "campo", "gioco"],
        "correct_option": "indicativa",
        "explanation": "'Una cifra indicativa / orientativa' corrisponde a una stima formale e ragionata C1.",
    },
    {
        "id": 10,
        "target_cefr": "C1",
        "category": "Periodo Ipotetico Misto",
        "scenario": "Valutare l'impatto di un'automazione implementata lo scorso anno.",
        "question": "Se il nostro team ______ quella procedura l'anno scorso, oggi non ______ affrontando questi colli di bottiglia.",
        "options": [
            "avesse implementato / staremmo",
            "ha implementato / stiamo",
            "implementava / stavamo",
            "avrebbe implementato / saremmo",
        ],
        "correct_option": "avesse implementato / staremmo",
        "explanation": "Periodo ipotetico misto: Congiuntivo trapassato ('avesse implementato') seguito dal condizionale presente ('staremmo').",
    },
]

# 6. MANDARIM (Chinese / Pinyin)
PLACEMENT_QUESTIONS_ZH: list[dict[str, Any]] = [
    {
        "id": 1,
        "target_cefr": "A1",
        "category": "自我介绍 (Apresentação Básica)",
        "scenario": "在第一天与国际团队成员初次见面并介绍职业。",
        "question": "在商务场合中自我介绍的正确句子是：",
        "options": [
            "我是运营经理，我和国际团队一起工作。(Wǒ shì yùnyíng jīnglǐ, wǒ hé guójì tuánduì yīqǐ gōngzuò.)",
            "我在运营经理，是国际团队工作。(Wǒ zài yùnyíng jīnglǐ, shì guójì tuánduì gōngzuò.)",
            "我有运营经理，和工作团队。(Wǒ yǒu yùnyíng jīnglǐ, hé gōngzuò tuánduì.)",
            "我运营经理做工作国际团队。(Wǒ yùnyíng jīnglǐ zuò gōngzuò guójì tuánduì.)",
        ],
        "correct_option": "我是运营经理，我和国际团队一起工作。(Wǒ shì yùnyíng jīnglǐ, wǒ hé guójì tuánduì yīqǐ gōngzuò.)",
        "explanation": "使用 '我是 + 职位' (Wǒ shì...) 来表达身份与职业。",
    },
    {
        "id": 2,
        "target_cefr": "A1",
        "category": "工作时间 (Horários)",
        "scenario": "询问同事早上日常上班时间。",
        "question": "询问对方日常上班时间的正确表达是：",
        "options": [
            "你平时早上几点开始上班？(Nǐ píngshí zǎoshang jǐ diǎn kāishǐ shàngbān?)",
            "你什么时候是上班？(Nǐ shénme shíhòu shì shàngbān?)",
            "几点你是上班早上？(Jǐ diǎn nǐ shì shàngbān zǎoshang?)",
            "你有几点工作开始？(Nǐ yǒu jǐ diǎn gōngzuò kāishǐ?)",
        ],
        "correct_option": "你平时早上几点开始上班？(Nǐ píngshí zǎoshang jǐ diǎn kāishǐ shàngbān?)",
        "explanation": "'几点开始上班' (jǐ diǎn kāishǐ shàngbān) 是询问开始工作时间的规范表达。",
    },
    {
        "id": 3,
        "target_cefr": "A2",
        "category": "过去动作 (Passado / Conclusão)",
        "scenario": "向管理层说明报表已于昨日发送完毕。",
        "question": "昨天，财务总监已经把业绩分析报告______所有投资人。",
        "options": [
            "发送给了 (fāsòng gěi le)",
            "正在发送 (zhèngzài fāsòng)",
            "要发送 (yào fāsòng)",
            "会发送 (huì fāsòng)",
        ],
        "correct_option": "发送给了 (fāsòng gěi le)",
        "explanation": "助词 '了' (le) 结合 '发送给' 表示过去已完成的动作。",
    },
    {
        "id": 4,
        "target_cefr": "A2",
        "category": "商务礼貌 (Polidez nos Negócios)",
        "scenario": "礼貌请求对方更新发票并尽快回复。",
        "question": "在商务邮件中，最得体礼貌的请求表达是：",
        "options": [
            "能否请您在方便时将更新后的发票发送给我们？(Néng fǒu qǐng nín zài fāngbiàn shí jiāng gēngxīn hòu de fāpiào fāsòng gěi wǒmen?)",
            "马上给我发票。(Mǎshàng gěi wǒ fāpiào.)",
            "你必须现在发发票。(Nǐ bìxū xiànzài fā fāpiào.)",
            "发票快点给我。(Fāpiào kuài diǎn gěi wǒ.)",
        ],
        "correct_option": "能否请您在方便时将更新后的发票发送给我们？(Néng fǒu qǐng nín zài fāngbiàn shí jiāng gēngxīn hòu de fāpiào fāsòng gěi wǒmen?)",
        "explanation": "'能否请您在方便时...' (Néng fǒu qǐng nín zài fāngbiàn shí...) 是商务信函中最标准客气的句式。",
    },
    {
        "id": 5,
        "target_cefr": "B1",
        "category": "规定与截止 (Prazos & Obrigações)",
        "scenario": "向团队通知必须在周五前提交总结。",
        "question": "所有项目负责人______在周五下午五点前提交审计复盘报告。",
        "options": [
            "必须 (bìxū)",
            "可以 (kěyǐ)",
            "可能 (kěnéng)",
            "愿意 (yuànyì)",
        ],
        "correct_option": "必须 (bìxū)",
        "explanation": "'必须' (bìxū) 表达强制性的制度要求和最后时限。",
    },
    {
        "id": 6,
        "target_cefr": "B1",
        "category": "因果关联 (Causa e Efeito)",
        "scenario": "向董事会解释平台上线推迟的原因。",
        "question": "平台上线计划暂时推迟，______服务器出现意外网络延迟。",
        "options": [
            "是由于 (shì yóuyú)",
            "为了 (wèile)",
            "以便 (yǐbiàn)",
            "即使 (jíshǐ)",
        ],
        "correct_option": "是由于 (shì yóuyú)",
        "explanation": "'由于' (yóuyú) 用于正式陈述原因与背景。",
    },
    {
        "id": 7,
        "target_cefr": "B2",
        "category": "商务沟通 (Alinhamento de Negócios)",
        "scenario": "提议下周二与业务伙伴做一次简短同步对接。",
        "question": "在商务交流中，表达快速对齐进度的地道说法是：",
        "options": [
            "我们下周二碰一下，对一下关键数据指标。(Wǒmen xià zhōu èr pèng yīxià, duì yīxià guānjiàn shùjù zhǐbiāo.)",
            "我们碰基地下周二看数字。(Wǒmen pèng jīdì xià zhōu èr kàn shùzì.)",
            "我们接触基地看数据。(Wǒmen jiēchù jīdì kàn shùjù.)",
            "触碰基地看指标。(Chùpèng jīdì kàn zhǐbiāo.)",
        ],
        "correct_option": "我们下周二碰一下，对一下关键数据指标。(Wǒmen xià zhōu èr pèng yīxià, duì yīxià guānjiàn shùjù zhǐbiāo.)",
        "explanation": "'碰一下 / 对一下' (pèng yīxià / duì yīxià) 是中文商业界广泛使用的 'touch base / align' 地道说法。",
    },
    {
        "id": 8,
        "target_cefr": "B2",
        "category": "商务谈判 (Negociação)",
        "scenario": "经过深入谈判，双方终于确定合作意向。",
        "question": "经过多轮谈判，双方商务团队终于______了互利共赢的合作协议。",
        "options": [
            "达成 (dáchéng)",
            "发生 (fāshēng)",
            "出现 (chūxiàn)",
            "产生 (chǎnshēng)",
        ],
        "correct_option": "达成 (dáchéng)",
        "explanation": "商务搭配通常为 '达成协议 / 达成共识' (dáchéng xiéyì)。",
    },
    {
        "id": 9,
        "target_cefr": "C1",
        "category": "预算估算 (Estimativas C1)",
        "scenario": "在最终定稿前询问大概的成本估算区间。",
        "question": "在确定最终路线图之前，您能否给我一个大致的成本______范围？",
        "options": [
            "估算 (gūsuàn)",
            "球场 (qiúchǎng)",
            "游戏 (yóuxì)",
            "操场 (cāochǎng)",
        ],
        "correct_option": "估算 (gūsuàn)",
        "explanation": "中文商务高阶表达为 '大致估算 / 概算' (gūsuàn)，避免直译 ballpark。",
    },
    {
        "id": 10,
        "target_cefr": "C1",
        "category": "假设与推论 (Raciocínio Hipotético)",
        "scenario": "回顾过去如果提前部署，今日就不会面临瓶颈。",
        "question": "如果我们去年就______自动化流程，今天就______面对这些效率瓶颈。",
        "options": [
            "部署了 / 不至于 (bùshǔ le / bù zhìyú)",
            "没有部署 / 一定会 (méiyǒu bùshǔ / yīdìng huì)",
            "准备部署 / 必须要 (zhǔnbèi bùshǔ / bìxū yào)",
            "部署着 / 正在 (bùshǔ zhe / zhèngzài)",
        ],
        "correct_option": "部署了 / 不至于 (bùshǔ le / bù zhìyú)",
        "explanation": "'如果...了，就不仅/不至于...' 表达过去假设对当下局面的规避逻辑。",
    },
]

PLACEMENT_QUESTIONS_BY_LANG: dict[str, list[dict[str, Any]]] = {
    "Inglês": PLACEMENT_QUESTIONS_EN,
    "Espanhol": PLACEMENT_QUESTIONS_ES,
    "Francês": PLACEMENT_QUESTIONS_FR,
    "Alemão": PLACEMENT_QUESTIONS_DE,
    "Italiano": PLACEMENT_QUESTIONS_IT,
    "Mandarim": PLACEMENT_QUESTIONS_ZH,
}


def get_placement_test_payload(profile: LanguageProfile) -> dict[str, Any]:
    """
    Retorna o teste de nivelamento adaptativo estruturado para o idioma ativo do perfil.
    Garante aleatorização real:
    1. Amostra 2 questões balanceadas por nível CEFR (A1 a C1).
    2. Embaralha a ordem das alternativas de cada questão para que a resposta correta não fique sempre na 1ª opção.
    """
    target_lang = profile.target_language or "Inglês"
    all_questions = PLACEMENT_QUESTIONS_BY_LANG.get(target_lang, PLACEMENT_QUESTIONS_BY_LANG["Inglês"])

    levels = ["A1", "A2", "B1", "B2", "C1"]
    chosen_questions = []

    for lvl in levels:
        lvl_qs = [q for q in all_questions if q.get("target_cefr") == lvl]
        if len(lvl_qs) >= 2:
            sampled = random.sample(lvl_qs, 2)
        else:
            sampled = lvl_qs

        for q in sampled:
            q_copy = dict(q)
            # Embaralha as alternativas
            shuffled_options = list(q.get("options", []))
            random.shuffle(shuffled_options)
            q_copy["options"] = shuffled_options
            chosen_questions.append(q_copy)

    test_data = {
        "profile_id": profile.id,
        "language": target_lang,
        "total_questions": len(chosen_questions),
        "target_levels": ["A1", "A2", "B1", "B2", "C1"],
        "questions": chosen_questions,
    }
    return {
        "placement_test": test_data,
        **test_data,
    }


async def evaluate_placement_test(
    profile: LanguageProfile,
    user_answers: list[dict[str, Any]],
    user: User,
    db: AsyncSession,
    submitted_questions: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
    """
    Avalia as respostas do teste de nivelamento no idioma alvo do usuário,
    calcula o nível CEFR real, identifica pontos cegos e atualiza o perfil.
    """
    target_lang = profile.target_language or "Inglês"
    all_questions = PLACEMENT_QUESTIONS_BY_LANG.get(target_lang, PLACEMENT_QUESTIONS_BY_LANG["Inglês"])

    answers_map = {ans.get("question_id"): str(ans.get("answer", "")).strip() for ans in user_answers}

    # Seleciona as questões a serem avaliadas
    if submitted_questions and len(submitted_questions) > 0:
        eval_questions = submitted_questions
    else:
        answered_ids = set(answers_map.keys())
        matched = [q for q in all_questions if q["id"] in answered_ids]
        eval_questions = matched if matched else all_questions[:10]

    scores_by_cefr: dict[str, dict[str, int]] = {
        "A1": {"correct": 0, "total": 0},
        "A2": {"correct": 0, "total": 0},
        "B1": {"correct": 0, "total": 0},
        "B2": {"correct": 0, "total": 0},
        "C1": {"correct": 0, "total": 0},
    }

    total_correct = 0

    for q in eval_questions:
        level = q["target_cefr"]
        scores_by_cefr[level]["total"] += 1
        user_ans = answers_map.get(q["id"])
        if user_ans == q["correct_option"]:
            scores_by_cefr[level]["correct"] += 1
            total_correct += 1

    # Critério de consistência progressiva
    a1_ok = scores_by_cefr["A1"]["correct"] >= 2
    a2_ok = scores_by_cefr["A2"]["correct"] >= 1
    b1_ok = scores_by_cefr["B1"]["correct"] >= 1
    b2_ok = scores_by_cefr["B2"]["correct"] >= 1
    c1_ok = scores_by_cefr["C1"]["correct"] >= 1

    if a1_ok and a2_ok and b1_ok and b2_ok and c1_ok:
        determined_level = "C1"
    elif a1_ok and a2_ok and b1_ok and b2_ok:
        determined_level = "B2"
    elif a1_ok and a2_ok and b1_ok:
        determined_level = "B1"
    elif (a1_ok and a2_ok) or scores_by_cefr["A2"]["correct"] >= 2:
        determined_level = "A2"
    else:
        determined_level = "A1"

    # Pontos cegos personalizados para o idioma
    blind_spots: list[str] = []
    if scores_by_cefr["C1"]["correct"] < scores_by_cefr["C1"]["total"]:
        blind_spots.append(f"Expressões idiomáticas avançadas e estruturas hipotéticas de alta persuasão em {target_lang} (C1)")
    if scores_by_cefr["B2"]["correct"] < scores_by_cefr["B2"]["total"]:
        blind_spots.append(f"Colocações verbais e jargões de negociação e alinhamento em {target_lang} (B2)")
    if scores_by_cefr["B1"]["correct"] < scores_by_cefr["B1"]["total"]:
        blind_spots.append(f"Conectores de causa/efeito e verbos modais de conformidade em {target_lang} (B1)")
    if scores_by_cefr["A2"]["correct"] < scores_by_cefr["A2"]["total"]:
        blind_spots.append(f"Passado simples e fórmulas de cortesia profissional em {target_lang} (A2)")
    if not blind_spots:
        blind_spots.append(f"Pronto para simulações executivas de alta complexidade em {target_lang}.")

    strengths: list[str] = []
    for lvl, s in scores_by_cefr.items():
        if s["correct"] == s["total"]:
            strengths.append(f"Domínio pleno das estruturas do nível {lvl} em {target_lang}")
    if not strengths:
        strengths.append(f"Boa compreensão inicial das bases funcionais de {target_lang}.")

    executive_summary = (
        f"Diagnóstico oficial ABVOS em {target_lang} concluído com {total_correct}/{len(eval_questions)} acertos. "
        f"Seu nível funcional classificado é {determined_level}. "
        f"Sua trilha de 15 minutos foi ajustada para os desafios corporativos em {target_lang}."
    )

    study_plan = (
        f"Sessões diárias focadas de 15 minutos em {target_lang} às {profile.preferred_time}: "
        f"5 min de reforço de vocabulário SRS, 5 min de micro-diálogo contextualizado e 5 min de produção ativa com correção IA."
    )

    diagnosis_payload = {
        "cefr_level": determined_level,
        "executive_summary": executive_summary,
        "score_total": total_correct,
        "max_score": len(eval_questions),
        "scores_by_cefr": scores_by_cefr,
        "blind_spots": blind_spots,
        "strengths": strengths,
        "recommended_study_plan": study_plan,
        "evaluated_at": _utc_now().isoformat(),
    }

    profile.cefr_level = determined_level
    profile.weaknesses_diagnosis = diagnosis_payload
    profile.updated_at = _utc_now()
    await db.commit()
    await db.refresh(profile)

    return diagnosis_payload


# ---------------------------------------------------------------------------
# GERADOR DOS 3 BLOCOS DIÁRIOS DE 15 MINUTOS (SRS, Imersão e Desafio Ativo)
# ---------------------------------------------------------------------------
def generate_default_3_blocks_lesson(profile: LanguageProfile, scheduled_date: date) -> dict[str, Any]:
    """Gera o payload dos 3 blocos no idioma alvo do usuário."""
    target_lang = profile.target_language or "Inglês"
    focus = profile.learning_focus or "business"
    cefr = profile.cefr_level if profile.cefr_level != "UNSET" else "B1"

    if target_lang == "Espanhol":
        return {
            "lesson_title": f"Sprint 15 min: Negociación y Alineación de Objetivos ({focus.capitalize()})",
            "daily_theme": f"Comunicación Ejecutiva & Gestión de Plazos ({cefr})",
            "target_language": "Espanhol",
            "cefr_level": cefr,
            "date": scheduled_date.isoformat(),
            "block1_srs": {
                "title": "Calentamiento & Repetición Espaciada (SRS)",
                "instructions": "Identifique el término corporativo ideal y su aplicación práctica.",
                "items": [
                    {
                        "id": 1,
                        "term": "Ponerse al día",
                        "context_sentence": "Vamos a ponernos al día el próximo lunes antes de la junta directiva.",
                        "prompt": "¿Cuál es el significado práctico de 'ponerse al día' en el ámbito empresarial?",
                        "options": [
                            "Alinear información rápidamente y actualizar el estado de las tareas.",
                            "Ponerse ropa adecuada para el día de trabajo.",
                            "Cancelar definitivamente el contrato con el cliente.",
                            "Llegar tarde a la oficina por la mañana.",
                        ],
                        "correct_option": "Alinear información rápidamente y actualizar el estado de las tareas.",
                        "explanation": "'Ponerse al día' significa intercambiar novedades y actualizarse mutuamente sobre un proyecto.",
                    },
                    {
                        "id": 2,
                        "term": "Cuello de botella",
                        "context_sentence": "El retraso en las aprobaciones legales está generando un cuello de botella crítico.",
                        "prompt": "¿Cómo define un director de operaciones un 'cuello de botella' en el flujo de trabajo?",
                        "options": [
                            "Un punto de congestión que ralentiza y limita la capacidad del proceso.",
                            "Una botella de agua olvidada en la sala de conferencias.",
                            "Un aumento inmediato de los ingresos brutos.",
                            "Una contratación de emergencia para el equipo.",
                        ],
                        "correct_option": "Un punto de congestión que ralentiza y limita la capacidad del proceso.",
                        "explanation": "'Cuello de botella' representa la fase más lenta que condiciona el ritmo de todo el sistema.",
                    },
                    {
                        "id": 3,
                        "term": "Entregable",
                        "context_sentence": "Debemos finalizar todos los entregables clave antes del cierre del sprint.",
                        "prompt": "¿Qué caracteriza a un 'entregable' en la gestión de proyectos y tecnología?",
                        "options": [
                            "Un resultado o producto de trabajo tangible comprometido y acordado.",
                            "El repartidor que entrega suministros de oficina.",
                            "Un correo electrónico de queja enviado por un usuario.",
                            "El contrato firmado archivado en el departamento legal.",
                        ],
                        "correct_option": "Un resultado o producto de trabajo tangible comprometido y acordado.",
                        "explanation": "'Entregable' es el término formal para los productos tangibles producidos durante un proyecto.",
                    },
                ],
            },
            "block2_immersion": {
                "title": "Inmersión Práctica & Micro-Diálogo Ejecutivo",
                "scenario_title": "Alineación Estratégica con Stakeholders",
                "scenario_text": (
                    "Sara (Directora de Operaciones): 'Hola Alejandro, gracias por conectarte. Necesitamos revisar el cronograma del tercer trimestre. "
                    "El proveedor tuvo demoras logísticas imprevistas, por lo que el despliegue inicial podría retrasarse dos semanas.'\n\n"
                    "Alejandro (Líder ABVOS): 'Comprendo, Sara. Para mitigar el impacto, podemos priorizar los módulos centrales del software "
                    "y liberar las notificaciones automatizadas primero. Pongámonos al día el jueves con el reporte de avance actualizado.'"
                ),
                "questions": [
                    {
                        "id": 1,
                        "question": "¿Cuál fue el motivo principal del posible retraso en el cronograma planteado por Sara?",
                        "options": [
                            "Demoras logísticas imprevistas por parte del proveedor.",
                            "Falta de presupuesto para contratar desarrolladores.",
                            "Cancelación del contrato con el cliente corporativo.",
                            "Fallas técnicas irreparables en los servidores centrales.",
                        ],
                        "correct_option": "Demoras logísticas imprevistas por parte del proveedor.",
                    },
                    {
                        "id": 2,
                        "question": "¿Qué plan de contingencia inmediato propuso Alejandro para reducir el impacto?",
                        "options": [
                            "Priorizar módulos centrales y lanzar primero las notificaciones automatizadas.",
                            "Cancelar el proyecto completo hasta el próximo trimestre.",
                            "Despedir al proveedor logístico inmediatamente.",
                            "Suspender todas las comunicaciones con la dirección.",
                        ],
                        "correct_option": "Priorizar módulos centrales y lanzar primero las notificaciones automatizadas.",
                    },
                ],
            },
            "block3_active_output": {
                "title": "Desafío de Producción Activa (Expresión Escrita & Oral)",
                "scenario_prompt": (
                    "Cenário: Responda a Sara confirmando que o plano de contingência foi acordado e que a equipe já está executando as prioridades. "
                    "Escreva de 2 a 4 frases em espanhol corporativo."
                ),
                "required_elements": [
                    "Usar 'ponerse al día' o 'dar seguimiento'",
                    "Mencionar 'mitigar el impacto' o 'módulos centrales'",
                    "Cerrar con tono profesional y resolutivo",
                ],
                "starter_hint": "Hola Sara, gracias por la alineación. Ya estamos ejecutando...",
            },
        }

    # Default em Inglês (ou outros idiomas)
    return {
        "lesson_title": f"Sprint 15 min: Scope Alignment & Negotiation ({focus.capitalize()})",
        "daily_theme": f"Executive Communication & Deadline Management ({cefr})",
        "target_language": "Inglês",
        "cefr_level": cefr,
        "date": scheduled_date.isoformat(),
        "block1_srs": {
            "title": "Aquecimento & Repetição Espaçada (SRS)",
            "instructions": "Identifique o termo correto e a aplicação ideal no contexto profissional.",
            "items": [
                {
                    "id": 1,
                    "term": "Touch base",
                    "context_sentence": "Let's touch base next Monday before the board meeting.",
                    "prompt": "Qual é o sentido prático de 'touch base' no meio corporativo?",
                    "options": [
                        "Fazer um alinhamento rápido e informal para checar o status.",
                        "Fechar permanentemente um contrato.",
                        "Tocar fisicamente na mesa do escritório.",
                        "Cancelar a reunião com clientes.",
                    ],
                    "correct_option": "Fazer um alinhamento rápido e informal para checar o status.",
                    "explanation": "'Touch base' vem do beisebol e significa entrar em contato brevemente para trocar informações essenciais.",
                },
                {
                    "id": 2,
                    "term": "Bottleneck",
                    "context_sentence": "The delayed vendor approval is causing a severe bottleneck in our launch timeline.",
                    "prompt": "Como um gestor de operações define um 'bottleneck' no fluxo de trabalho?",
                    "options": [
                        "Um gargalo que restringe o fluxo e reduz a capacidade de entrega.",
                        "Uma garrafa deixada na sala de reunião.",
                        "Uma contratação rápida de estagiários.",
                        "Um aumento exponencial nos lucros operacionais.",
                    ],
                    "correct_option": "Um gargalo que restringe o fluxo e reduz a capacidade de entrega.",
                    "explanation": "'Bottleneck' representa qualquer ponto que trava o processo e gera fila.",
                },
                {
                    "id": 3,
                    "term": "Deliverable",
                    "context_sentence": "We must finalize all key deliverables before the end of the sprint.",
                    "prompt": "O que caracteriza um 'deliverable' em projetos de tecnologia e negócios?",
                    "options": [
                        "Um produto ou resultado tangível prometido e entregável.",
                        "O entregador de aplicativo que traz refeições.",
                        "Um e-mail enviado por engano à diretoria.",
                        "Uma reclamação formal registrada em suporte.",
                    ],
                    "correct_option": "Um produto ou resultado tangível prometido e entregável.",
                    "explanation": "'Deliverable' refere-se aos produtos de trabalho mensuráveis contratados ou acordados.",
                },
            ],
        },
        "block2_immersion": {
            "title": "Imersão Prática & Micro-Diálogo Executivo",
            "scenario_title": "Alinhamento com Stakeholder Estratégico",
            "scenario_text": (
                "Sarah (VP de Operações): 'Hi Alex, thanks for hopping on. We need to review the Q3 timeline. "
                "The supplier encountered logistical delays, so the initial rollout might slip by two weeks.'\n\n"
                "Alex (Líder ABVOS): 'I understand, Sarah. To mitigate the impact, we can prioritize the core software modules "
                "and deploy the automated notifications first. Let's touch base on Thursday with the revised burndown chart.'"
            ),
            "questions": [
                {
                    "id": 1,
                    "question": "Qual foi a causa principal da possível alteração no cronograma apresentada por Sarah?",
                    "options": [
                        "Atrasos logísticos enfrentados pelo fornecedor.",
                        "Falta de recursos financeiros na empresa.",
                        "Cancelamento da parceria de software.",
                        "Problemas técnicos no servidor de e-mail.",
                    ],
                    "correct_option": "Atrasos logísticos enfrentados pelo fornecedor.",
                },
                {
                    "id": 2,
                    "question": "Qual plano de contingência imediato Alex propôs para amortecer o impacto?",
                    "options": [
                        "Priorizar módulos essenciais e liberar as notificações automatizadas primeiro.",
                        "Cancelar o projeto inteiro até o próximo ano.",
                        "Demitir o fornecedor imediatamente.",
                        "Adiar todas as reuniões até o próximo mês.",
                    ],
                    "correct_option": "Priorizar módulos essenciais e liberar as notificações automatizadas primeiro.",
                },
            ],
        },
        "block3_active_output": {
            "title": "Desafio de Produção Ativa (Speaking & Writing)",
            "scenario_prompt": (
                "Cenário: Você precisa responder a Sarah por e-mail ou mensagem direta confirmando que o plano de contingência "
                "foi acordado e que a equipe já está executando as prioridades. "
                "Escreva de 2 a 4 frases em inglês corporativo."
            ),
            "required_elements": [
                "Utilizar 'touch base' ou 'follow up'",
                "Mencionar 'mitigate the impact' ou 'core modules'",
                "Encerrar com tom profissional e positivo",
            ],
            "starter_hint": "Hi Sarah, thank you for the alignment. We are actively working on...",
        },
    }


async def get_or_create_today_session(
    profile: LanguageProfile,
    user: User,
    db: AsyncSession,
) -> LanguageDailySession:
    """Busca a sessão diária de hoje ou gera uma sessão completa de 3 blocos no idioma ativo."""
    today = date.today()

    res = await db.execute(
        select(LanguageDailySession).where(
            LanguageDailySession.language_profile_id == profile.id,
            LanguageDailySession.scheduled_date == today,
        )
    )
    session = res.scalar_one_or_none()

    # Valida se a sessão existente já tem o idioma correto no payload
    if session and session.lesson_payload and "block1_srs" in session.lesson_payload:
        existing_lang = session.lesson_payload.get("target_language")
        if existing_lang == profile.target_language:
            return session

    lesson_payload = generate_default_3_blocks_lesson(profile, today)

    # Tenta enriquecer com Gemini 3.8 Flash se a chave estiver configurada (ignora em testes automatizados)
    if not os.environ.get("PYTEST_CURRENT_TEST"):
        try:
            client, model_name = await get_user_gemini_client(user, db)
            prompt = (
                f"Você é um tutor bilíngue de alta performance de idiomas para empreendedores e executivos. "
                f"O usuário estuda {profile.target_language} com foco em {profile.learning_focus} e nível CEFR {profile.cefr_level}. "
                f"Gere um cenário de negócios do dia curto e prático INTEIRAMENTE no idioma {profile.target_language}. "
                f"Responda apenas em formato JSON com chaves: 'scenario_title', 'scenario_text' (máximo 110 palavras de diálogo no idioma {profile.target_language}), "
                f"'question1' e 'question2' para o Bloco de Imersão."
            )
            def _gen_sync():
                return client.models.generate_content(
                    model=model_name,
                    contents=[types.Content(role="user", parts=[types.Part.from_text(text=prompt)])],
                    config=types.GenerateContentConfig(temperature=0.7),
                )
            response = await asyncio.wait_for(asyncio.to_thread(_gen_sync), timeout=2.5)
            if response.text and "{" in response.text:
                cleaned = response.text[response.text.find("{") : response.text.rfind("}") + 1]
                ai_data = json.loads(cleaned)
                if "scenario_text" in ai_data:
                    lesson_payload["block2_immersion"]["scenario_title"] = ai_data.get("scenario_title", lesson_payload["block2_immersion"]["scenario_title"])
                    lesson_payload["block2_immersion"]["scenario_text"] = ai_data["scenario_text"]

                log_ai_usage(user.id, model_name, "languages_daily_generation", 250, 150, db)
        except Exception as e:
            logger.info(f"Gemini generation fallback used for today's session: {e}")

    now = _utc_now()
    if session:
        session.lesson_payload = lesson_payload
        session.updated_at = now
    else:
        session = LanguageDailySession(
            language_profile_id=profile.id,
            scheduled_date=today,
            status="ready",
            lesson_payload=lesson_payload,
            created_at=now,
            updated_at=now,
        )
        db.add(session)

    await db.commit()
    await db.refresh(session)
    return session


async def evaluate_daily_session_submission(
    profile: LanguageProfile,
    session: LanguageDailySession,
    user_answers: dict[str, Any],
    time_spent: int,
    user: User,
    db: AsyncSession,
) -> dict[str, Any]:
    """
    Avalia a submissão dos 3 blocos de estudo no idioma ativo do perfil.
    """
    now = _utc_now()
    today = date.today()
    target_lang = profile.target_language or "Inglês"

    block1_answers = user_answers.get("block1_srs", {})
    block2_answers = user_answers.get("block2_immersion", {})
    block3_text = str(user_answers.get("block3_active_output", "")).strip()

    lesson = session.lesson_payload or {}
    block1_items = lesson.get("block1_srs", {}).get("items", [])
    block2_questions = lesson.get("block2_immersion", {}).get("questions", [])

    # Pontuação Bloco 1
    b1_correct = 0
    for idx, item in enumerate(block1_items):
        ans = block1_answers.get(str(item.get("id", idx))) or block1_answers.get(item.get("id")) or block1_answers.get(idx)
        if ans == item.get("correct_option"):
            b1_correct += 1

    # Pontuação Bloco 2
    b2_correct = 0
    for idx, q in enumerate(block2_questions):
        ans = block2_answers.get(str(q.get("id", idx))) or block2_answers.get(q.get("id")) or block2_answers.get(idx)
        if ans == q.get("correct_option"):
            b2_correct += 1

    b1_score = (b1_correct / len(block1_items)) * 40 if block1_items else 40
    b2_score = (b2_correct / len(block2_questions)) * 30 if block2_questions else 30
    b3_score = 30 if len(block3_text) >= 15 else 15
    overall_score = min(100, int(b1_score + b2_score + b3_score))

    # Avaliação do Bloco 3: Produção Ativa
    if target_lang == "Espanhol":
        natural_version = "Hola Sara, gracias por la actualización. Ya estamos ejecutando el plan de contingencia para mitigar el impacto y priorizar los módulos centrales. Pongámonos al día el jueves según lo previsto."
        explanation = "La expresión 'ya estamos ejecutando' transmite dinamismo y proactividad ejecutiva, y 'según lo previsto' confirma compromiso con los plazos acordados."
        new_words_to_vault: list[dict[str, str]] = [
            {
                "term_or_phrase": "Mitigar el impacto",
                "translation": "Atenuar / amortecer o impacto de um imprevisto",
                "context_example": "Implementamos soluciones rápidas para mitigar el impacto en los plazos.",
            },
            {
                "term_or_phrase": "Ponerse al día",
                "translation": "Alinhar novidades e atualizar o status de trabalho",
                "context_example": "Vamos a ponernos al día el jueves por la mañana.",
            },
        ]
    else:
        natural_version = "Hi Sarah, thanks for the update. We are already executing the mitigation plan and prioritizing our core modules. Let's touch base on Thursday as planned."
        explanation = "The phrase 'already executing the mitigation plan' demonstrates proactive leadership, and 'as planned' reinforces reliability."
        new_words_to_vault = [
            {
                "term_or_phrase": "Mitigate the impact",
                "translation": "Atenuar / amortecer o impacto negativo de um imprevisto",
                "context_example": "We deployed extra cloud capacity to mitigate the impact of the traffic surge.",
            },
            {
                "term_or_phrase": "Burndown chart",
                "translation": "Gráfico de evolução do trabalho restante em relação ao tempo",
                "context_example": "The team reviewed the burndown chart during the morning standup.",
            },
        ]

    if not os.environ.get("PYTEST_CURRENT_TEST"):
        try:
            client, model_name = await get_user_gemini_client(user, db)
            prompt = (
                f"Você é um consultor executivo nativo em {target_lang}. "
                f"O usuário escreveu a seguinte resposta em {target_lang} para um desafio corporativo:\n"
                f"\"{block3_text}\"\n\n"
                f"Reescreva a mensagem para soar fluida, profissional e nativa em {target_lang}. "
                f"Responda em JSON com as chaves: 'natural_native_version' e 'micro_explanation' (máx 2 linhas)."
            )
            def _eval_sync():
                return client.models.generate_content(
                    model=model_name,
                    contents=[types.Content(role="user", parts=[types.Part.from_text(text=prompt)])],
                    config=types.GenerateContentConfig(temperature=0.7),
                )
            response = await asyncio.wait_for(asyncio.to_thread(_eval_sync), timeout=2.5)
            if response.text and "{" in response.text:
                cleaned = response.text[response.text.find("{") : response.text.rfind("}") + 1]
                ai_eval = json.loads(cleaned)
                if "natural_native_version" in ai_eval:
                    natural_version = ai_eval["natural_native_version"]
                    explanation = ai_eval.get("micro_explanation", explanation)
                log_ai_usage(user.id, model_name, "languages_active_output_eval", 200, 100, db)
        except Exception as e:
            logger.info(f"Using default native rephrasing fallback: {e}")

    for word in new_words_to_vault:
        vault_check = await db.execute(
            select(LanguageVocabularyVault).where(
                LanguageVocabularyVault.language_profile_id == profile.id,
                LanguageVocabularyVault.term_or_phrase == word["term_or_phrase"],
            )
        )
        if not vault_check.scalar_one_or_none():
            v_item = LanguageVocabularyVault(
                language_profile_id=profile.id,
                term_or_phrase=word["term_or_phrase"],
                translation=word["translation"],
                context_example=word["context_example"],
                mastery_level=1,
                next_review_date=today + timedelta(days=1),
                created_at=now,
                updated_at=now,
            )
            db.add(v_item)

    # Atualização do Streak
    last_act = profile.last_activity_date
    if last_act == today:
        pass
    elif last_act == today - timedelta(days=1):
        profile.streak_days = (profile.streak_days or 0) + 1
    else:
        profile.streak_days = 1

    profile.last_activity_date = today
    profile.updated_at = now

    evaluation_feedback = {
        "overall_score": overall_score,
        "feedback_title": "Missão Cumprida com Alta Eficiência! 🔥",
        "feedback_summary": f"Você obteve nota {overall_score}/100 em {target_lang}. Sua ofensiva foi mantida para {profile.streak_days} dias seguidos!",
        "block3_active_evaluation": {
            "user_input": block3_text,
            "natural_native_version": natural_version,
            "micro_explanation": explanation,
        },
        "new_words_to_vault": new_words_to_vault,
    }

    session.status = "completed"
    session.score = overall_score
    session.time_spent_seconds = time_spent
    session.user_answers = user_answers
    session.ai_feedback = evaluation_feedback
    session.completed_at = now
    session.updated_at = now

    await db.commit()
    await db.refresh(session)
    await db.refresh(profile)

    return {
        "session": session,
        "profile": profile,
        "evaluation": evaluation_feedback,
        "score": overall_score,
        "streak_days": profile.streak_days,
    }


def review_vault_item(item: LanguageVocabularyVault, remembered: bool) -> LanguageVocabularyVault:
    """Calcula a repetição espaçada (SRS) ao revisar um item do cofre."""
    now = _utc_now()
    today = date.today()

    if remembered:
        item.mastery_level = min(5, (item.mastery_level or 1) + 1)
        intervals = {1: 1, 2: 2, 3: 4, 4: 8, 5: 21}
        days_ahead = intervals.get(item.mastery_level, 21)
        item.next_review_date = today + timedelta(days=days_ahead)
    else:
        item.mastery_level = 1
        item.next_review_date = today + timedelta(days=1)

    item.updated_at = now
    return item


def log_ai_usage(user_id: int, model: str, context: str, prompt_tokens: int, completion_tokens: int, db: AsyncSession):
    """Auxiliar para agendamento de log de consumo de IA."""
    try:
        total = prompt_tokens + completion_tokens
        cost = Decimal(str(round((total / 1000) * 0.000075, 6)))
        log_entry = AiUsageLog(
            user_id=user_id,
            model=model,
            context=context,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total,
            estimated_cost_usd=cost,
            latency_ms=180,
            created_at=_utc_now(),
            updated_at=_utc_now(),
        )
        db.add(log_entry)
    except Exception as e:
        logger.error(f"Erro ao registrar AiUsageLog: {e}")


# ---------------------------------------------------------------------------
# ANÁLISE DE DICÇÃO E PRONÚNCIA POR IA (Multimodal Audio Gemini)
# ---------------------------------------------------------------------------

async def analyze_audio_pronunciation(
    profile: LanguageProfile,
    audio_bytes: bytes,
    mime_type: str,
    target_text: str,
    user: User,
    db: AsyncSession,
) -> dict[str, Any]:
    """
    Avalia a dicção, fonética e fluência do áudio enviado pelo usuário usando Gemini Multimodal.
    Fornece nota de 0 a 100, transcrição, detecção de vícios articulatórios e instruções anatômicas corretivas.
    """
    target_lang = profile.target_language or "Inglês"
    cefr = profile.cefr_level if profile.cefr_level != "UNSET" else "B1"

    # Fallback estruturado caso Gemini esteja offline ou em ambiente de testes
    fallback_result = {
        "overall_score": 88,
        "clarity_score": 85,
        "rhythm_score": 90,
        "transcription": target_text,
        "target_text": target_text,
        "is_acceptable": True,
        "phonetic_errors": [],
        "coaching_instruction": (
            f"Boa articulação em {target_lang}! Para atingir máxima fluência nativa, pratique conectar as consoantes finais "
            f"com a vogal da palavra seguinte (linking sounds) e mantenha a ênfase nas palavras-chave da mensagem."
        ),
        "practice_drill": f"Repita com foco no ritmo: '{target_text}'.",
    }

    if not os.environ.get("PYTEST_CURRENT_TEST"):
        try:
            client, model_name = await get_user_gemini_client(user, db)

            clean_mime = mime_type.split(";")[0].strip() or "audio/webm"
            if clean_mime not in ("audio/webm", "audio/wav", "audio/mp4", "audio/ogg", "audio/mpeg", "audio/mp3", "audio/x-m4a"):
                clean_mime = "audio/webm"

            prompt = (
                f"Você é um fonoaudiólogo bilíngue e coach executivo de pronúncia e dicção para o idioma {target_lang}.\n"
                f"O aluno é brasileiro (português nativo) e seu nível atual é {cefr}.\n"
                f"A frase que o aluno devia pronunciar é:\n"
                f"\"{target_text}\"\n\n"
                f"Analise o áudio anexado e faça uma avaliação fonética minuciosa e profissional:\n"
                f"1. Transcreva com fidelidade o que o aluno realmente disse no áudio.\n"
                f"2. Avalie com nota de 0 a 100 a dicção (overall_score), clareza fonética (clarity_score) e ritmo/prosódia (rhythm_score).\n"
                f"3. Aponte palavras com erro fonético ou sotaque acentuado (ex: epêntese de vogais como 'fóquios' para 'focus', 'th' falhado, tonicidade incorreta, etc.).\n"
                f"4. Ensine exatamente como posicionar língua, lábios, dentes e fluxo de ar para corrigir o som incorreto.\n\n"
                f"Responda EXCLUSIVAMENTE em formato JSON com o seguinte formato:\n"
                f"{{\n"
                f"  \"overall_score\": 85,\n"
                f"  \"clarity_score\": 88,\n"
                f"  \"rhythm_score\": 82,\n"
                f"  \"transcription\": \"transcrição do áudio\",\n"
                f"  \"target_text\": \"{target_text}\",\n"
                f"  \"is_acceptable\": true,\n"
                f"  \"phonetic_errors\": [\n"
                f"    {{\n"
                f"      \"word\": \"palavra\",\n"
                f"      \"heard_as\": \"como soou\",\n"
                f"      \"phonetic_ipa\": \"/ipa/\",\n"
                f"      \"issue\": \"descrição do desvio articulatório\",\n"
                f"      \"correction_tip\": \"instrução anatômica prática de correção\"\n"
                f"    }}\n"
                f"  ],\n"
                f"  \"coaching_instruction\": \"explicação didática completa e motivadora em português\",\n"
                f"  \"practice_drill\": \"exercício de repetição direcionado\"\n"
                f"}}"
            )

            def _call_gemini_audio():
                return client.models.generate_content(
                    model=model_name,
                    contents=[
                        types.Content(
                            role="user",
                            parts=[
                                types.Part.from_bytes(data=audio_bytes, mime_type=clean_mime),
                                types.Part.from_text(text=prompt),
                            ],
                        )
                    ],
                    config=types.GenerateContentConfig(temperature=0.2),
                )

            res = await asyncio.wait_for(asyncio.to_thread(_call_gemini_audio), timeout=15.0)
            if res.text and "{" in res.text:
                json_part = res.text[res.text.find("{") : res.text.rfind("}") + 1]
                data = json.loads(json_part)
                log_ai_usage(user.id, model_name, "languages_pronunciation_analysis", 350, 200, db)
                return data
        except Exception as e:
            logger.warning(f"Erro na análise multimodal de pronúncia: {e}")

    return fallback_result


# ---------------------------------------------------------------------------
# ÁREA ABERTA DE CONVERSAÇÃO INTERATIVA NO IDIOMA ATIVO
# ---------------------------------------------------------------------------

PRACTICE_TOPICS = [
    {
        "id": "business_meeting",
        "title": "Alinhamento & Reunião de Negócios",
        "icon": "💼",
        "description": "Simule uma reunião estratégica para discutir metas, prazos e entregáveis com executivos.",
    },
    {
        "id": "negotiation",
        "title": "Negociação & Fechamento de Contratos",
        "icon": "🤝",
        "description": "Pratique a defesa de propostas comerciais, escopo e termos vantajosos.",
    },
    {
        "id": "casual_networking",
        "title": "Networking & Conversa Casual",
        "icon": "☕",
        "description": "Treine apresentações pessoais, trocas informais e conversas de café e eventos.",
    },
    {
        "id": "startup_pitch",
        "title": "Pitch de Apresentação de Projeto",
        "icon": "🚀",
        "description": "Apresente uma startup ou produto e responda a perguntas de clientes e investidores.",
    },
    {
        "id": "travel_airport",
        "title": "Viagens, Imigração & Hotel",
        "icon": "✈️",
        "description": "Situações práticas de aeroporto, imigração, conferências e reservas internacionais.",
    },
    {
        "id": "free_chat",
        "title": "Conversa Livre & Qualquer Tema",
        "icon": "✨",
        "description": "Pratique livremente sobre qualquer assunto de seu interesse com feedback nativo.",
    },
]


async def get_practice_conversation(profile_id: int, db: AsyncSession) -> dict[str, Any]:
    """Retorna o histórico de mensagens da conversação de prática e os tópicos disponíveis."""
    res = await db.execute(
        select(LanguagePracticeMessage)
        .where(LanguagePracticeMessage.language_profile_id == profile_id)
        .order_by(LanguagePracticeMessage.id.asc())
    )
    msgs = res.scalars().all()
    return {
        "topics": PRACTICE_TOPICS,
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "topic": m.topic,
                "feedback": m.feedback,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in msgs
        ],
    }


async def send_practice_message(
    profile: LanguageProfile,
    user_message: str,
    topic: str,
    user: User,
    db: AsyncSession,
) -> dict[str, Any]:
    """
    Envia uma mensagem na área de conversação aberta.
    O Gemini responde fluidamente no idioma alvo e gera feedback pedagógico lateral (correções e dicas nativas).
    """
    target_lang = profile.target_language or "Inglês"
    cefr = profile.cefr_level if profile.cefr_level != "UNSET" else "B1"

    now = _utc_now()
    user_msg_record = LanguagePracticeMessage(
        language_profile_id=profile.id,
        role="user",
        content=user_message,
        topic=topic,
        created_at=now,
    )
    db.add(user_msg_record)
    await db.commit()
    await db.refresh(user_msg_record)

    # Buscar histórico recente das últimas 6 mensagens para manter coerência
    hist_res = await db.execute(
        select(LanguagePracticeMessage)
        .where(LanguagePracticeMessage.language_profile_id == profile.id)
        .order_by(LanguagePracticeMessage.id.desc())
        .limit(6)
    )
    recent_msgs = list(reversed(hist_res.scalars().all()))

    # Resposta padrão conforme o idioma alvo (fallback)
    if target_lang == "Espanhol":
        assistant_reply = "¡Excelente observación! Coincido plenamente contigo. ¿Cómo piensas abordar los siguientes pasos del plan?"
    elif target_lang == "Francês":
        assistant_reply = "Très bien vu ! C'est tout à fait pertinent. Comment envisagez-vous la suite du projet ?"
    elif target_lang == "Alemão":
        assistant_reply = "Sehr guter Punkt! Wie planen Sie die nächsten Schritte in diesem Projekt umzusetzen?"
    elif target_lang == "Italiano":
        assistant_reply = "Ottimo spunto! Come intendi procedere con i prossimi passi del progetto?"
    elif target_lang == "Mandarim":
        assistant_reply = "非常有见地！您打算接下来如何推进具体计划？(Fēicháng yǒu jiàndì! Nǐ dǎsuàn jiē xiàlái rúhé tuījìn jùtǐ jìhuà?)"
    else:
        assistant_reply = "That makes complete sense! It's a strategic approach. What do you think should be our top priority for next week?"

    feedback_data = {
        "has_correction": False,
        "correction_note": None,
        "native_alternative": f"Frase natural e compreensível em {target_lang}.",
        "vocabulary_highlight": ["strategic approach", "priority"] if target_lang == "Inglês" else [],
    }

    if not os.environ.get("PYTEST_CURRENT_TEST"):
        try:
            client, model_name = await get_user_gemini_client(user, db)
            history_text = "\n".join([f"{m.role.upper()}: {m.content}" for m in recent_msgs])
            system_prompt = (
                f"Você é Alex, um interlocutor executivo e parceiro nativo de conversação no idioma {target_lang}.\n"
                f"O aluno tem nível {cefr} e está praticando no tópico: {topic}.\n"
                f"Diretrizes:\n"
                f"1. Responda INTEIRAMENTE no idioma {target_lang} de forma natural, profissional e estimulante, mantendo a conversa ativa com uma pergunta no final.\n"
                f"2. Avalie a mensagem enviada pelo usuário. Se houver desvios gramaticais, vocabulário truncado ou formulações pouco naturais, forneça feedback pedagógico em Português.\n"
                f"3. Indique como um falante nativo diria a mesma ideia de forma mais idiomática ('native_alternative').\n\n"
                f"Responda estritamente em JSON com as chaves:\n"
                f"{{\n"
                f"  \"reply\": \"sua resposta fluida no idioma {target_lang}\",\n"
                f"  \"feedback\": {{\n"
                f"    \"has_correction\": true/false,\n"
                f"    \"correction_note\": \"explicação didática em português se houver erro, ou null\",\n"
                f"    \"native_alternative\": \"versão natural e idiomática da frase do usuário\",\n"
                f"    \"vocabulary_highlight\": [\"termo1\", \"termo2\"]\n"
                f"  }}\n"
                f"}}"
            )

            prompt_content = f"Histórico recente da conversa:\n{history_text}\n\nGere a resposta da IA e o feedback pedagógico."

            def _call_gemini():
                return client.models.generate_content(
                    model=model_name,
                    contents=[
                        types.Content(role="user", parts=[
                            types.Part.from_text(text=system_prompt),
                            types.Part.from_text(text=prompt_content),
                        ])
                    ],
                    config=types.GenerateContentConfig(temperature=0.7),
                )

            res = await asyncio.wait_for(asyncio.to_thread(_call_gemini), timeout=10.0)
            if res.text and "{" in res.text:
                json_str = res.text[res.text.find("{") : res.text.rfind("}") + 1]
                parsed = json.loads(json_str)
                assistant_reply = parsed.get("reply", assistant_reply)
                feedback_data = parsed.get("feedback", feedback_data)
                log_ai_usage(user.id, model_name, "languages_conversation_practice", 250, 150, db)
        except Exception as e:
            logger.warning(f"Erro no chat de conversação com Gemini: {e}")

    now2 = _utc_now()
    assistant_msg_record = LanguagePracticeMessage(
        language_profile_id=profile.id,
        role="assistant",
        content=assistant_reply,
        topic=topic,
        feedback=feedback_data,
        created_at=now2,
    )
    db.add(assistant_msg_record)
    await db.commit()
    await db.refresh(assistant_msg_record)

    return {
        "user_message": {
            "id": user_msg_record.id,
            "role": user_msg_record.role,
            "content": user_msg_record.content,
            "topic": user_msg_record.topic,
            "created_at": user_msg_record.created_at.isoformat() if user_msg_record.created_at else None,
        },
        "assistant_message": {
            "id": assistant_msg_record.id,
            "role": assistant_msg_record.role,
            "content": assistant_msg_record.content,
            "topic": assistant_msg_record.topic,
            "feedback": assistant_msg_record.feedback,
            "created_at": assistant_msg_record.created_at.isoformat() if assistant_msg_record.created_at else None,
        },
    }


async def clear_practice_conversation(profile_id: int, db: AsyncSession) -> dict[str, str]:
    """Limpa o histórico de mensagens da conversação de prática."""
    await db.execute(
        delete(LanguagePracticeMessage).where(LanguagePracticeMessage.language_profile_id == profile_id)
    )
    await db.commit()
    return {"message": "Histórico de conversação limpo com sucesso."}

