import Swal from 'sweetalert2'

const darkSwal = Swal.mixin({
  background: '#0f172a', // slate-900
  color: '#f8fafc',      // slate-50
  confirmButtonColor: '#10b981', // emerald-500
  cancelButtonColor: '#475569',  // slate-600
  customClass: {
    popup: 'border border-slate-800 rounded-2xl shadow-2xl font-sans',
    title: 'text-lg font-bold text-slate-100',
    htmlContainer: 'text-sm text-slate-300',
    confirmButton: 'px-5 py-2.5 rounded-xl font-semibold text-sm shadow transition',
    cancelButton: 'px-5 py-2.5 rounded-xl font-semibold text-sm transition',
    input: 'bg-slate-950 text-slate-100 border-slate-700 rounded-xl focus:border-emerald-500',
  },
})

export function useSwal() {
  const toast = (title, icon = 'success') => {
    return darkSwal.fire({
      toast: true,
      position: 'top-end',
      showConfirmButton: false,
      timer: 3000,
      timerProgressBar: true,
      icon,
      title,
    })
  }

  const confirm = async ({
    title = 'Tem certeza?',
    text = 'Esta ação não poderá ser revertida.',
    confirmText = 'Sim, confirmar',
    cancelText = 'Cancelar',
    icon = 'warning',
  } = {}) => {
    const result = await darkSwal.fire({
      title,
      text,
      icon,
      showCancelButton: true,
      confirmButtonText: confirmText,
      cancelButtonText: cancelText,
      reverseButtons: true,
    })

    return result.isConfirmed
  }

  const promptRevision = async ({
    title = 'Solicitar Ajuste ao Gemini 3.8',
    defaultSection = 'all',
  } = {}) => {
    const { value: formValues } = await darkSwal.fire({
      title,
      html: `
        <div class="text-left text-xs text-slate-400 mb-3">
          Indique qual seção você deseja que o agente reescreva e descreva com detalhes o ajuste:
        </div>
        <div class="mb-4 text-left">
          <label class="block text-xs font-semibold text-slate-300 mb-1">Seção a ajustar:</label>
          <select id="swal-section" class="w-full bg-slate-950 text-slate-200 border border-slate-700 rounded-lg p-2 text-sm focus:outline-none focus:border-emerald-500">
            <option value="all" ${defaultSection === 'all' ? 'selected' : ''}>Pacote Completo</option>
            <option value="hooks" ${defaultSection === 'hooks' ? 'selected' : ''}>Apenas os Hooks (Ganchos dos primeiros 3s)</option>
            <option value="script" ${defaultSection === 'script' ? 'selected' : ''}>Roteiro Cena-a-Cena</option>
            <option value="visual_prompts" ${defaultSection === 'visual_prompts' ? 'selected' : ''}>Prompts Visuais / Instruções de Câmera</option>
            <option value="caption" ${defaultSection === 'caption' ? 'selected' : ''}>Legenda e Hashtags</option>
            <option value="cta" ${defaultSection === 'cta' ? 'selected' : ''}>Chamada para Ação (CTA)</option>
          </select>
        </div>
        <div class="text-left">
          <label class="block text-xs font-semibold text-slate-300 mb-1">Instruções para a IA:</label>
          <textarea id="swal-feedback" rows="4" placeholder="Ex: Deixe o hook mais agressivo focando na dor de perder tempo, e adicione uma piada sutil no segundo 8..." class="w-full bg-slate-950 text-slate-200 border border-slate-700 rounded-lg p-3 text-sm focus:outline-none focus:border-emerald-500"></textarea>
        </div>
      `,
      showCancelButton: true,
      confirmButtonText: 'Enviar para o Agente',
      cancelButtonText: 'Cancelar',
      confirmButtonColor: '#6366f1', // indigo-500
      preConfirm: () => {
        const section = document.getElementById('swal-section').value
        const feedback = document.getElementById('swal-feedback').value.trim()

        if (!feedback) {
          Swal.showValidationMessage('Descreva as instruções de ajuste para o agente.')
          return false
        }

        return { section, feedback }
      },
    })

    return formValues || null
  }

  const success = (title, text = '') => {
    return darkSwal.fire({
      icon: 'success',
      title,
      text,
    })
  }

  const error = (title, text = '') => {
    return darkSwal.fire({
      icon: 'error',
      title,
      text,
    })
  }

  return {
    swal: darkSwal,
    toast,
    confirm,
    promptRevision,
    success,
    error,
  }
}

