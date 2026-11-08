const { chromium } = require('../frontend/node_modules/playwright');
const path = require('path');
const fs = require('fs');

const SCREENSHOTS_DIR = '/home/spira/.gemini/antigravity/brain/3a88b790-2e5e-4a2b-b4b9-4009f4a9d920/screenshots';
const BASE_URL = 'http://localhost:8080';

if (!fs.existsSync(SCREENSHOTS_DIR)) {
  fs.mkdirSync(SCREENSHOTS_DIR, { recursive: true });
}

async function runVisualSweep() {
  console.log('🚀 Iniciando Varredura Visual & Testes E2E de Fluxos...');
  console.log(`📁 Diretório de Screenshots: ${SCREENSHOTS_DIR}`);
  console.log(`🌐 Alvo: ${BASE_URL}`);

  const browser = await chromium.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage'],
  });

  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    locale: 'pt-BR',
  });

  const page = await context.newPage();

  const consoleErrors = [];
  const networkErrors = [];

  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      consoleErrors.push({ text: msg.text(), location: msg.location() });
      console.log(`❌ [CONSOLE ERROR]: ${msg.text()}`);
    }
  });

  page.on('pageerror', (err) => {
    consoleErrors.push({ text: err.message, stack: err.stack });
    console.log(`💥 [PAGE EXCEPTION]: ${err.message}`);
  });

  page.on('response', (response) => {
    const status = response.status();
    const url = response.url();
    // Filtra erros esperados de teste de credenciais incorretas (/api/auth/login 401 ou 422)
    if (status >= 400 && !url.includes('/api/auth/login') && !url.includes('/favicon.ico')) {
      networkErrors.push({ url, status });
      console.log(`⚠️ [HTTP ${status}]: ${url}`);
    }
  });

  async function snap(name) {
    const file = path.join(SCREENSHOTS_DIR, `${name}.png`);
    await page.waitForTimeout(500);
    await page.screenshot({ path: file, fullPage: true });
    console.log(`📸 Screenshot capturado: ${name}.png`);
  }

  try {
    // -------------------------------------------------------------
    // FLUXO 1: TELA DE LOGIN & VALIDAÇÕES DE CREDENCIAIS
    // -------------------------------------------------------------
    console.log('\n--- 1. Testando Fluxo de Login ---');
    await page.goto(`${BASE_URL}/login`, { waitUntil: 'networkidle' });
    await snap('01_login_page');

    // Tentar login com credenciais incorretas
    await page.fill('input[type="email"]', 'invalido@spirandeli.com');
    await page.fill('input[type="password"]', 'SenhaErrada123!');
    await page.click('button[type="submit"]');
    await page.waitForTimeout(1000);
    await snap('02_login_error_credentials');

    // -------------------------------------------------------------
    // FLUXO 2: TELA DE REGISTRO & VALIDAÇÃO DE SENHA DIVERGENTE
    // -------------------------------------------------------------
    console.log('\n--- 2. Testando Fluxo de Registro ---');
    await page.goto(`${BASE_URL}/register`, { waitUntil: 'networkidle' });
    await snap('03_register_page');

    await page.fill('input[placeholder*="Alexander"]', 'Alexander Teste');
    await page.fill('input[placeholder*="dominio.com"]', 'alexander.teste@spirandeliempire.tech');
    const passInputs = await page.$$('input[type="password"]');
    if (passInputs.length >= 2) {
      await passInputs[0].fill('Spirandeli2026!');
      await passInputs[1].fill('Divergente2026!');
      await page.click('button[type="submit"]');
      await page.waitForTimeout(600);
      await snap('04_register_password_mismatch');
    }

    // -------------------------------------------------------------
    // FLUXO 3: LOGIN COM SUCESSO (ADMINISTRADOR)
    // -------------------------------------------------------------
    console.log('\n--- 3. Autenticando com Conta Executiva ---');
    await page.goto(`${BASE_URL}/login`, { waitUntil: 'networkidle' });
    await page.fill('input[type="email"]', 'spirandelidev@gmail.com');
    await page.fill('input[type="password"]', 'Spirandeli2026!');
    await page.click('button[type="submit"]');
    await page.waitForURL(`${BASE_URL}/`, { timeout: 10000 });
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);
    await snap('05_dashboard_cockpit');

    // -------------------------------------------------------------
    // FLUXO 4: COCKPIT EXECUTIVO & PROVISIONAMENTO DE SHOWCASE
    // -------------------------------------------------------------
    console.log('\n--- 4. Testando Ações do Dashboard ---');
    // Clicar em "Carregar Showcase Demo"
    const showcaseBtn = await page.$('button:has-text("Showcase")');
    if (showcaseBtn) {
      await showcaseBtn.click();
      await page.waitForTimeout(2500);
      await page.waitForSelector('.swal2-container', { state: 'detached', timeout: 3000 }).catch(() => {});
      await snap('06_dashboard_showcase_loaded');
    }

    // Abertura do Drawer de Chat IA
    const chatBtn = await page.$('button:has-text("Falar com COO IA")');
    if (chatBtn) {
      await chatBtn.click();
      await page.waitForTimeout(800);
      await snap('07_chat_drawer_opened');
      // Fechar drawer
      const closeDrawer = await page.$('button[aria-label="Fechar Drawer COO"]');
      if (closeDrawer) {
        await closeDrawer.click();
      } else {
        await page.keyboard.press('Escape');
      }
      await page.waitForTimeout(600);
    }

    // -------------------------------------------------------------
    // FLUXO 5: HUB DE NEGÓCIOS & MODAL DE NOVO VENTURE
    // -------------------------------------------------------------
    console.log('\n--- 5. Testando Hub de Negócios (/businesses) ---');
    await page.goto(`${BASE_URL}/businesses`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(1000);
    await snap('08_businesses_index');

    // Abrir Modal de Criação de Negócio
    const newBizBtn = await page.$('button:has-text("Novo Venture")') || await page.$('button:has-text("Lançar")');
    if (newBizBtn) {
      await newBizBtn.click();
      await page.waitForTimeout(600);
      await snap('09_create_business_modal');

      // Testar validação de campo obrigatório vazio
      const submitBizBtn = await page.$('div[class*="fixed"] button[type="submit"]');
      if (submitBizBtn) {
        // Tentar enviar com nome vazio
        await page.fill('input[placeholder*="Gadgets Virais"]', '');
        await submitBizBtn.click();
        await page.waitForTimeout(600);
        await snap('10_create_business_validation_error');
        // Fechar alerta do SweetAlert se houver
        const swalConfirm = await page.$('.swal2-confirm');
        if (swalConfirm) await swalConfirm.click();
        await page.waitForTimeout(400);
      }

      // Preencher formulário válido
      await page.fill('input[placeholder*="Gadgets Virais"]', 'Tech Nova Venture');
      await page.fill('input[placeholder*="Utilidades"]', 'Gadgets & IA');
      await page.fill('textarea[placeholder*="Descreva o propósito"]', 'Operação de afiliados de alta escala no TikTok Shop');
      if (submitBizBtn) {
        await submitBizBtn.click();
        await page.waitForTimeout(3000);
        await snap('11_business_created_detail');
      }
    }

    // -------------------------------------------------------------
    // FLUXO 6: DETALHES DO NEGÓCIO & ABAS
    // -------------------------------------------------------------
    console.log('\n--- 6. Testando Detalhes do Negócio & Abas ---');
    // Navegar pelas abas
    const tiktokTab = await page.$('button:has-text("Vitrine TikTok Shop")') || await page.$('button:has-text("TikTok")');
    if (tiktokTab) {
      await tiktokTab.click();
      await page.waitForTimeout(800);
      await snap('12_business_tab_tiktok');

      // Testar botão Minerar Produtos
      const mineBtn = await page.$('button:has-text("Minerar")');
      if (mineBtn) {
        await mineBtn.click();
        await page.waitForTimeout(1000);
        await snap('13_business_mining_action');
      }
    }

    const growthTab = await page.$('button:has-text("Growth")') || await page.$('button:has-text("ROI")');
    if (growthTab) {
      await growthTab.click();
      await page.waitForTimeout(800);
      await snap('14_business_tab_growth');
    }

    const autoTab = await page.$('button:has-text("Automações Cron")') || await page.$('button:has-text("Automações")');
    if (autoTab) {
      await autoTab.click();
      await page.waitForTimeout(800);
      await snap('15_business_tab_automations');

      // Testar toggle de automação
      const toggleBtn = await page.$('button:has-text("Ativa")') || await page.$('button:has-text("Pausada")');
      if (toggleBtn) {
        await toggleBtn.click();
        await page.waitForTimeout(1000);
        await snap('16_business_automation_toggled');
      }
    }

    const tasksTab = await page.$('button:has-text("Operações & Tarefas")') || await page.$('button:has-text("Tarefas")');
    if (tasksTab) {
      await tasksTab.click();
      await page.waitForTimeout(800);
      await snap('17_business_tab_tasks');
    }

    // -------------------------------------------------------------
    // FLUXO 7: OPERAÇÕES KANBAN & CRIAR TAREFA
    // -------------------------------------------------------------
    console.log('\n--- 7. Testando Operações Kanban (/tasks) ---');
    await page.goto(`${BASE_URL}/tasks`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(1000);
    await snap('18_tasks_board');

    // Modal Nova Tarefa
    const newTaskBtn = await page.$('button:has-text("Nova Tarefa")');
    if (newTaskBtn) {
      await newTaskBtn.click();
      await page.waitForTimeout(600);
      await snap('19_create_task_modal');

      // Teste de validação: título vazio
      const submitTaskBtn = await page.$('div[class*="fixed"] button[type="submit"]');
      if (submitTaskBtn) {
        await page.fill('input[placeholder*="Gravar vídeo"]', '');
        await submitTaskBtn.click();
        await page.waitForTimeout(600);
        await snap('20_create_task_validation_error');
        const swalConfirmTask = await page.$('.swal2-confirm');
        if (swalConfirmTask) await swalConfirmTask.click();
        await page.waitForTimeout(600);
        await page.waitForSelector('.swal2-container', { state: 'detached', timeout: 3000 }).catch(() => {});
      }

      // Preenchimento com dados válidos
      await page.fill('input[placeholder*="Gravar vídeo"]', 'Validar Criativo Viral 01');
      await page.fill('textarea[placeholder*="Instruções"]', 'Gravar primeiros 3 segundos com hook de quebra de padrão.');
      if (submitTaskBtn) {
        await submitTaskBtn.click();
        await page.waitForTimeout(2500);
        await page.waitForSelector('.swal2-container', { state: 'detached', timeout: 3000 }).catch(() => {});
        await snap('21_task_created_on_board');
      }
    }

    // Toggle Terminal de Logs da IA
    const logsToggleBtn = await page.$('button:has-text("Logs da IA")');
    if (logsToggleBtn) {
      await logsToggleBtn.click({ force: true });
      await page.waitForTimeout(600);
      await snap('22_terminal_logs_toggled');
    }

    // -------------------------------------------------------------
    // FLUXO 8: ACADEMIA DE IDIOMAS & FLUXO ADAPTATIVO
    // -------------------------------------------------------------
    console.log('\n--- 8. Testando Academia de Idiomas (/languages) ---');
    await page.goto(`${BASE_URL}/languages`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(1500);
    await snap('23_languages_academy');

    // Verificar se modal de onboarding ou nivelamento abriu
    const onboardingHeader = await page.$('h2:has-text("Onboarding")');
    if (onboardingHeader) {
      await snap('24_language_onboarding_modal');
      // Avançar passo 1
      const nextBtn1 = await page.$('button:has-text("Avançar para Rotina")');
      if (nextBtn1) await nextBtn1.click();
      await page.waitForTimeout(600);
      // Avançar passo 2
      const finishOnboarding = await page.$('button:has-text("Concluir e Iniciar Nivelamento")');
      if (finishOnboarding) await finishOnboarding.click();
      await page.waitForTimeout(2000);
      await snap('25_language_placement_test_modal');

      // Fechar modal de teste para inspecionar as abas
      const closeTestBtn = await page.$('button[title="Fechar teste"]');
      if (closeTestBtn) {
        await closeTestBtn.click();
        await page.waitForTimeout(600);
      }
    }

    // Fechar qualquer modal de nivelamento aberto antes de alternar abas
    const openCloseBtn = await page.$('button[title="Fechar teste"]') || await page.$('button[title="Fechar"]');
    if (openCloseBtn) {
      await openCloseBtn.click();
      await page.waitForTimeout(600);
    }

    // Alternar abas da Academia de Idiomas
    const vaultTab = await page.$('button:has-text("Cofre SRS")');
    if (vaultTab) {
      await vaultTab.click();
      await page.waitForTimeout(800);
      await snap('26_language_vault_tab');
    }

    const diagTab = await page.$('button:has-text("Diagnóstico & CEFR")');
    if (diagTab) {
      await diagTab.click();
      await page.waitForTimeout(800);
      await snap('27_language_diagnosis_tab');
    }

    // -------------------------------------------------------------
    // FLUXO 9: CALENDÁRIO RFC 5545 ZERO-AUTH DEMO
    // -------------------------------------------------------------
    console.log('\n--- 9. Testando Calendário Zero-Auth RFC 5545 (/calendar/demo) ---');
    await page.goto(`${BASE_URL}/calendar/demo`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(1000);
    await snap('28_calendar_demo');

    // Abrir Modal de Sincronização Geral
    const generalSyncBtn = await page.$('button:has-text("Abrir Modal de Sincronização Geral")');
    if (generalSyncBtn) {
      await generalSyncBtn.click();
      await page.waitForTimeout(800);
      await snap('29_calendar_sync_modal');

      // Testar botão copiar feed URL
      const copyFeedBtn = await page.$('button:has-text("Copiar URL")');
      if (copyFeedBtn) {
        await copyFeedBtn.click();
        await page.waitForTimeout(600);
        await snap('30_calendar_feed_copied');
      }

      // Fechar modal
      const closeSyncBtn = await page.$('button:has-text("Concluir")');
      if (closeSyncBtn) await closeSyncBtn.click();
      await page.waitForTimeout(500);
    }

    // -------------------------------------------------------------
    // FLUXO 10: CONFIGURAÇÕES & INTEGRAÇÕES
    // -------------------------------------------------------------
    console.log('\n--- 10. Testando Configurações & Integrações (/settings/integrations) ---');
    await page.goto(`${BASE_URL}/settings/integrations`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(1000);
    await snap('31_settings_integrations');

    // Testar validação de Apple CalDAV com campos vazios
    const saveAppleBtn = await page.$('button:has-text("Salvar Conexão CalDAV")');
    if (saveAppleBtn) {
      await saveAppleBtn.click();
      await page.waitForTimeout(600);
      await snap('32_apple_caldav_validation_alert');
      // Fechar sweetalert se aberto
      const swalOk = await page.$('.swal2-confirm');
      if (swalOk) await swalOk.click();
      await page.waitForTimeout(400);
    }

    // Testar geração de token Apple Shortcuts
    const tokenGenBtn = await page.$('button:has-text("Gerar Novo Token")');
    if (tokenGenBtn) {
      await tokenGenBtn.click();
      await page.waitForTimeout(1500);
      await snap('33_shortcuts_token_generated');
    }

    // -------------------------------------------------------------
    // FLUXO 11: GOVERNANÇA IA ADMINISTRATIVA
    // -------------------------------------------------------------
    console.log('\n--- 11. Testando Governança IA Administrativa (/admin/ai-governance) ---');
    await page.goto(`${BASE_URL}/admin/ai-governance`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(1000);
    await snap('34_admin_ai_governance');

    // Clicar em Editar Cota de um usuário
    const editLimitBtn = await page.$('button:has-text("Editar Cota")');
    if (editLimitBtn) {
      await editLimitBtn.click();
      await page.waitForTimeout(600);
      await snap('35_admin_edit_quota_modal');
      const cancelSwal = await page.$('.swal2-cancel');
      if (cancelSwal) await cancelSwal.click();
      await page.waitForTimeout(400);
    }

    // -------------------------------------------------------------
    // FLUXO 12: AÇÕES GLOBAIS DA BARRA LATERAL & LOGOUT
    // -------------------------------------------------------------
    console.log('\n--- 12. Testando Ações Globais & Logout ---');
    // Testar Kill-Switch Global dos Workers
    const killSwitchStatus = await page.$('span:has-text("ONLINE")') || await page.$('span:has-text("PAUSED")');
    if (killSwitchStatus) {
      await killSwitchStatus.click();
      await page.waitForTimeout(600);
      await snap('36_global_killswitch_confirm_modal');
      const cancelKill = await page.$('.swal2-cancel');
      if (cancelKill) await cancelKill.click();
      await page.waitForTimeout(1000);
    }

    // Garante fechamento de qualquer container residual do swal
    const residualSwal = await page.$('.swal2-container');
    if (residualSwal) {
      const cancelBtn = await page.$('.swal2-cancel') || await page.$('.swal2-confirm');
      if (cancelBtn) await cancelBtn.click();
      await page.waitForTimeout(800);
    }

    // Logout
    const logoutBtn = await page.$('button:has-text("Sair do Sistema")');
    if (logoutBtn) {
      await logoutBtn.click();
      await page.waitForTimeout(1500);
      await snap('37_post_logout_login');
    }

    console.log('\n🎉 Varredura visual e testes de fluxo concluídos com sucesso!');
    console.log(`📊 Total de Erros de Console capturados: ${consoleErrors.length}`);
    console.log(`🌐 Total de Falhas de Rede HTTP capturadas: ${networkErrors.length}`);

  } catch (error) {
    console.error('💥 Erro fatal durante a execução dos testes:', error);
    await snap('99_error_fatal');
  } finally {
    await browser.close();
  }
}

runVisualSweep();
