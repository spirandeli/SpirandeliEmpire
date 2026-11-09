/**
 * Utilitário de Agrupamento Inteligente de Roteiros e Tarefas por Série / Vídeo
 * Suporta detecção via parent_id explícito e expressões regulares para padrões como:
 * - "Série Apocalipse - Cena 07: O Segundo Selo - A Espada e o Sangue"
 * - "Série Nephilim - Cena 04: Os Filhos dos Vigílias"
 * - "Vídeo X - Parte 1", "Projeto Alpha - Etapa 2", etc.
 */

const SCENE_SERIES_REGEX = /^(.*?)(?:\s*[-–—:]\s*(?:Cena|Epis[oó]dio|Parte|Part|Scene|Act|Ato)\s*(\d+)(?:\s*[-–—:]\s*(.*))?)?$/i

/**
 * Extrai informações estruturadas de série/vídeo mestre a partir do título.
 * @param {string} title
 * @returns {{ seriesTitle: string, isSeriesOrScene: boolean, sceneNumber: number|null, sceneTitle: string }}
 */
export function parseSeriesAndScene(title = '') {
  if (!title) {
    return { seriesTitle: 'Vídeo Sem Título', isSeriesOrScene: false, sceneNumber: null, sceneTitle: '' }
  }

  const match = title.trim().match(SCENE_SERIES_REGEX)
  if (match && match[2]) {
    const rawSeries = match[1].trim()
    const sceneNum = parseInt(match[2], 10)
    const sceneSubTitle = (match[3] || '').trim()
    return {
      seriesTitle: rawSeries || 'Série Principal',
      isSeriesOrScene: true,
      sceneNumber: isNaN(sceneNum) ? null : sceneNum,
      sceneTitle: sceneSubTitle || `Cena ${match[2]}`,
    }
  }

  return {
    seriesTitle: title.trim(),
    isSeriesOrScene: false,
    sceneNumber: null,
    sceneTitle: title.trim(),
  }
}

/**
 * Agrupa uma lista de roteiros/assets do Estúdio Dark por Série / Vídeo Mãe.
 * @param {Array} scripts
 * @returns {Array} Lista de itens agrupados (ou avulsos)
 */
export function groupDarkScripts(scripts = []) {
  if (!Array.isArray(scripts) || scripts.length === 0) return []

  const groupsMap = new Map()
  const standaloneItems = []

  // Primeira passagem: agrupar por parent_id explícito ou série detectada
  for (const s of scripts) {
    const { seriesTitle, isSeriesOrScene, sceneNumber, sceneTitle } = parseSeriesAndScene(s.title)

    // Chave de agrupamento: parent_id explícito ou nome normalizado da série
    const groupKey = s.parent_id ? `parent_${s.parent_id}` : (isSeriesOrScene ? seriesTitle.toLowerCase() : null)

    if (groupKey) {
      if (!groupsMap.has(groupKey)) {
        groupsMap.set(groupKey, {
          isGroup: true,
          groupKey,
          title: seriesTitle,
          format_type: s.format_type || 'short',
          target_platform: s.target_platform || 'youtube_shorts',
          seo_tags: new Set(),
          status: s.status,
          total_revenue_brl: 0,
          total_views: 0,
          created_at: s.created_at,
          items: [],
        })
      }

      const group = groupsMap.get(groupKey)
      // Agrega tags
      if (Array.isArray(s.seo_tags)) {
        s.seo_tags.forEach((t) => group.seo_tags.add(t))
      }
      group.total_revenue_brl += Number(s.total_revenue_brl || 0)
      group.total_views += Number(s.total_views || 0)

      // Atualiza data para a mais recente
      if (s.created_at && (!group.created_at || new Date(s.created_at) > new Date(group.created_at))) {
        group.created_at = s.created_at
      }

      // Adiciona o item enriquecido com metadados de cena
      group.items.push({
        ...s,
        parsedSceneNumber: sceneNumber ?? (group.items.length + 1),
        parsedSceneTitle: sceneTitle || s.title,
      })
    } else {
      standaloneItems.push({
        ...s,
        isGroup: false,
        items: [s],
      })
    }
  }

  const result = []

  // Processa os grupos identificados
  for (const group of groupsMap.values()) {
    // Ordena as cenas dentro do grupo pelo número da cena (ascendente)
    group.items.sort((a, b) => (a.parsedSceneNumber || 0) - (b.parsedSceneNumber || 0))

    // Se o grupo tem apenas 1 item e não tinha marcação explícita de série, podemos tratá-lo
    // Mas se o título expressamente era "Cena 01", mantém o grupo visualmente limpo
    group.seo_tags = Array.from(group.seo_tags)
    group.scenes_count = group.items.reduce((acc, curr) => acc + (curr.scenes_count || curr.scenes?.length || 1), 0)

    // Determina o status geral do grupo
    const allApproved = group.items.every((it) => it.status === 'approved' || it.status === 'published')
    const anySupervision = group.items.some((it) => it.status === 'supervision' || it.status === 'pending_approval' || it.status === 'pending')
    if (allApproved) {
      group.status = 'approved'
    } else if (anySupervision) {
      group.status = 'pending_approval'
    }

    // Gancho principal (pega da primeira cena ou do primeiro roteiro)
    group.hook = group.items[0]?.hook || ''
    group.full_narration = group.items.map((it) => it.full_narration).filter(Boolean).join('\n\n')

    result.push(group)
  }

  // Combina grupos e avulsos, ordenando pelos mais recentes
  const combined = [...result, ...standaloneItems]
  combined.sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0))

  return combined
}

/**
 * Agrupa tarefas do Kanban por Vídeo / Série / Projeto.
 * @param {Array} tasks
 * @returns {Array} Lista de tarefas agrupadas
 */
export function groupKanbanTasks(tasks = []) {
  if (!Array.isArray(tasks) || tasks.length === 0) return []

  const groupsMap = new Map()
  const standaloneTasks = []

  for (const t of tasks) {
    const { seriesTitle, isSeriesOrScene, sceneNumber, sceneTitle } = parseSeriesAndScene(t.title)
    const groupKey = t.parent_id ? `parent_${t.parent_id}` : (isSeriesOrScene ? seriesTitle.toLowerCase() : null)

    if (groupKey) {
      if (!groupsMap.has(groupKey)) {
        groupsMap.set(groupKey, {
          id: `group_${groupKey}`,
          isGroup: true,
          groupKey,
          title: seriesTitle,
          business: t.business,
          business_id: t.business_id,
          priority: t.priority || 'medium',
          assignee: t.assignee || 'agent',
          created_at: t.created_at,
          subtasks: [],
        })
      }

      const group = groupsMap.get(groupKey)
      group.subtasks.push({
        ...t,
        parsedSceneNumber: sceneNumber,
        parsedSceneTitle: sceneTitle,
      })

      // Eleva prioridade se alguma subtarefa for urgente/alta
      if (t.priority === 'urgent') group.priority = 'urgent'
      else if (t.priority === 'high' && group.priority !== 'urgent') group.priority = 'high'
    } else {
      standaloneTasks.push({
        ...t,
        isGroup: false,
        subtasks: [t],
      })
    }
  }

  const result = []
  for (const g of groupsMap.values()) {
    g.subtasks.sort((a, b) => (a.parsedSceneNumber || 0) - (b.parsedSceneNumber || 0))
    g.completedCount = g.subtasks.filter((st) => st.status === 'done' || st.status === 'completed').length
    g.totalCount = g.subtasks.length
    g.progressPercent = Math.round((g.completedCount / g.totalCount) * 100)
    result.push(g)
  }

  return [...result, ...standaloneTasks]
}
