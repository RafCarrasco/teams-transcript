# Ideias & Insights

Ideias levantadas além do roadmap atual. Não são decisões — são material para o
Rafael avaliar. Itens marcados com 🔑 são insights que podem mudar decisões de
arquitetura; vale ler antes de seguir a implementação.

---

## 🔑 1. O canal do microfone JÁ é o Rafael — diarização só no loopback

A captura grava dois canais separados: `mic` (o que o Rafael fala) e `loopback`
(o que sai dos alto-falantes = todos os outros). **O Rafael já vem isolado de
graça.** Não é preciso baseline de voz nem wizard de 30s para separar "Rafael ×
resto" — basta marcar tudo do canal `mic` como Rafael.

A diarização (pyannote) só é necessária para separar **os outros participantes
entre si** dentro do canal loopback. Isso simplifica a Fase 4: o caso comum (1:1)
nem precisa de diarização, e o caso de grupo roda pyannote só no loopback (mais
rápido, mais preciso, sem o baseline).

## 🔑 2. Privacidade do resumo no free tier do Gemini

O free tier do Google AI Studio **pode usar os dados enviados para melhorar os
modelos** — política diferente da API paga. O resumo manda o **texto da
transcrição** para o Google. Para calls sensíveis (M&A, contratos, dados
financeiros) isso é um risco concreto, e contradiz parcialmente o princípio de
privacidade do projeto.

Mitigações possíveis:
- Toggle por call: "não resumir esta call" / "resumo local apenas".
- Modo "privacidade total": desliga o resumo cloud; transcrição local continua.
- Redação antes de enviar: mascarar nomes próprios / valores antes do prompt.
- Resumo local opcional para calls marcadas como sensíveis (LLM pequeno).
- UI deixar explícito **quais** calls vão para a nuvem.

Decisão pendente do Rafael — ver seção "Perguntas em aberto".

## 🔑 3. Loopback específico do processo do Teams

WASAPI loopback padrão captura **tudo** que sai dos alto-falantes — incluindo
notificações do Windows, música, outro vídeo aberto. VAD ajuda, mas notificação
sonora parece fala.

Windows 10 2004+ permite **loopback por processo** (capturar só o áudio de um
PID). Capturar somente a sessão de áudio do processo do Teams isola a call do
resto do desktop. Vale investigar — melhora muito a qualidade do input do Whisper.

## 4. Detecção de call mais robusta

A heurística "RMS no loopback" (Fase 6) é frágil — música e vídeo também geram
RMS. Combinar sinais dá detecção bem mais limpa:
- Processo do Teams ativo (já implementado em `detection/teams.py`).
- Teams com **sessão de áudio ativa** (enumeração de sessões WASAPI via `pycaw`).
- Opcional: ler o calendário local do Outlook do próprio usuário para pré-armar
  a gravação quando há reunião agendada (não precisa de admin/Graph — é o
  calendário do próprio usuário).

## 5. Detecção de idioma por chunk

Whisper detecta o idioma no início e trava nele. Calls PT-BR↔EN trocam de idioma
no meio. Rodar detecção de idioma **por chunk** (não global) lida melhor com
code-switching do que só o `initial_prompt`.

## 6. Resumo incremental

Em vez de uma única chamada de LLM no fim da call, resumir a cada ~15 min em
background. Reduz a latência percebida no fim e mantém um resumo "vivo" durante
calls longas.

## 7. Action items viram tarefas

O resumo já estrutura action items como `[responsável]: [tarefa] (deadline)`.
Parsear isso e oferecer export com 1 clique. Começar simples: gerar `.ics`
(lembrete no calendário) ou integrar Todoist (API gratuita), antes de Linear/Jira.

## 8. Alternativas grátis ao Gemini

Se o rate limit do free tier do Gemini incomodar, outras opções cloud $0:
- **Groq** — Llama 3.3 70B, free tier, muito rápido.
- **Cerebras** — free tier.
- **OpenRouter** — alguns modelos gratuitos.
O campo `provider` no `settings.yaml` já deixa isso plugável.

## 9. Distribuição — modelo on-demand

O bundle estimado de ~300 MB é quase todo o modelo Whisper medium (300 MB).
Alternativa: installer leve (~30 MB) que baixa o modelo no primeiro uso. Melhor
UX de download e atualização independente do modelo.

## 10. Fixtures de teste sem call real

Bloqueio recorrente: validar transcrição/diarização exige call do Teams real.
Criar um conjunto de WAVs curtos de referência (gravados com consentimento, ou
sintéticos via TTS) permite testes de regressão de qualidade sem agendar call.
Para medir WER, a transcrição nativa do Teams numa call de teste serve como
ground truth aproximado.

## 11. Crash recovery do áudio

O writer append-only do transcript já está planejado. Estender ao áudio: gravar
o WAV em chunks (ex. 1 por minuto) em vez de um arquivo gigante aberto — se
crashar, os chunks até o ponto da falha ficam íntegros.

## 12. macOS sem driver de terceiro

BlackHole/Loopback são fricção de adoção. macOS 14.4+ tem Core Audio process
taps (`AudioHardwareCreateProcessTap`) — captura áudio de um processo específico
sem driver externo. Mais alinhado ao princípio "sem fricção" do que pedir para o
usuário instalar um driver de áudio.

---

## Perguntas em aberto (precisam do Rafael)

Estas precisam de decisão humana — não dá para resolver sozinho. Vale uma sessão
de brainstorming dedicada:

1. **Política da Procurement Garage** — bloqueia o uso? É o risco nº 1 do projeto
   e independe de qualquer código.
2. **Privacidade vs. Gemini free tier** — sabendo que o free tier pode usar os
   dados para treino, ok mandar transcripts para o Google? Ou o projeto precisa
   de um modo local-only para calls sensíveis desde o MVP? (ver insight 🔑 2)
3. **Disclosure default** — avisar os participantes por padrão, ou caso a caso?
4. **Retenção** — quanto tempo guardar transcrições por padrão?
5. **Escopo do MVP** — a simplificação do insight 🔑 1 (mic = Rafael) permite
   adiar a diarização para depois do MVP. Vale fazer isso?
