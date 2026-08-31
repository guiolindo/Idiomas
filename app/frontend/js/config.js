// Configuração local — não é segredo (a anon key do Supabase é pública por
// design, protegida pelas regras de RLS no banco), mas fica separada do
// código pra ser fácil de trocar por ambiente.

window.API_BASE = window.API_BASE || 'http://localhost:8000';

// Cole aqui a URL e a anon key do SEU projeto Supabase (supabase.com, plano
// free). Enquanto ficarem vazias, o app funciona normalmente, só sem login
// nem sincronização entre aparelhos — o progresso continua salvo no navegador.
// Veja app/README.md → "Ativar login" para o passo a passo.
window.SUPABASE_URL = '';
window.SUPABASE_ANON_KEY = '';
