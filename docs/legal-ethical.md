# Considerações Legais e Éticas

**Importante:** este documento é um guia de boas práticas, NÃO é aconselhamento jurídico. Antes de usar a ferramenta em ambiente corporativo, consulte o jurídico da empresa.

---

## 1. LGPD (Brasil)

A Lei Geral de Proteção de Dados (Lei 13.709/2018) regula tratamento de dados pessoais — e voz é dado pessoal.

### Pontos-chave

- **Princípio do consentimento** (Art. 7º, I): coleta requer consentimento do titular, OU bases legais alternativas (Art. 7º, IX cobre legítimo interesse)
- **Gravação de conversa por participante** (jurisprudência STF, RE 583.937): é lícito gravar conversa da qual você participa, mesmo sem aviso prévio, desde que não seja usada pra fins ilícitos
- **Single-party consent**: Brasil segue esse padrão na maior parte dos casos
- **Tratamento de dados**: se a transcrição é armazenada, você (Rafael) se torna controlador de dados

### Recomendações práticas

| Cenário | Recomendado? |
|---|---|
| Gravar call interna que você participa, para suas próprias notas | ✅ Sim |
| Avisar aos outros participantes ("estou usando transcrição local") | ✅ Boa prática |
| Compartilhar transcript com outros internamente | ⚠️ Pedir consentimento |
| Publicar trechos da call externamente | ❌ Sem consentimento explícito |
| Treinar modelos de IA com transcrições | ❌ Requer DPIA + consentimento |
| Gravar call onde você NÃO está presente | ❌ Ilegal (interceptação) |

---

## 2. Política corporativa

A Procurement Garage (ou qualquer empresa) pode ter regras internas mais restritivas que a lei.

**Antes de usar:**

1. Consultar manual do colaborador / código de conduta
2. Perguntar pro RH/jurídico se há policy sobre gravação de reuniões
3. Verificar se o cliente / vendor tem cláusulas contratuais sobre confidencialidade

**Cenários que provavelmente precisam de aviso:**

- Reuniões com clientes externos
- Reuniões com vendors/fornecedores
- Calls que discutem dados financeiros, contratos, M&A
- Calls com participantes em jurisdições mais restritivas (UE com GDPR, Califórnia com CCPA)

**Cenários geralmente OK sem aviso (internamente):**

- Reuniões internas de equipe
- 1:1 com seu time
- Calls de planning / standup

---

## 3. Microsoft Teams ToS

O Acordo de Serviços da Microsoft não proíbe captura externa de áudio do sistema. Mas:

- A funcionalidade nativa de "Record" exibe aviso visual e legal
- Bypassar isso via captura local NÃO viola ToS, mas pode violar política da org que paga a licença Teams
- Microsoft Graph API pra gravação requer admin consent — fora do escopo dessa ferramenta

---

## 4. GDPR (UE, se houver participantes europeus)

Mais restritivo que LGPD. Inclui:

- **Direito ao esquecimento**: usuário pode pedir deleção
- **Consentimento explícito antes da coleta**
- **Notificação de breach** em 72h

**Recomendação**: se houver participante europeu na call, comunicar explicitamente e ter opt-out fácil.

---

## 5. Design da ferramenta refletindo essas considerações

A arquitetura proposta já incorpora salvaguardas:

| Salvaguarda | Como funciona |
|---|---|
| Local-first | Áudio nunca sai do disco do usuário; só resumo (opcional) usa Claude |
| Warning na primeira execução | UI mostra texto explicando responsabilidade do usuário em disclosure |
| Setting opt-out de áudio raw | Após transcrever, pode deletar o WAV automaticamente |
| Sem cloud sync por default | Storage local; sync manual via export |
| Retention configurável | Default 365 dias, configurável (ou "forever" / "30 days") |
| Logs anonimizados | Logs de debug não capturam conteúdo transcrito |
| Criptografia opcional | Fase futura: AES nas transcripts em disco |

---

## 6. Disclosure templates

Frases prontas pra usar antes de gravar:

**Português (informal, time interno):**
> "Galera, só pra avisar: estou usando uma ferramenta local de transcrição pra ter notas dessa call. Fica tudo na minha máquina, sem cloud. Alguém prefere que eu desligue?"

**Português (formal, cliente):**
> "Antes de começarmos, gostaria de informar que utilizo uma ferramenta interna de transcrição automatizada para apoio às minhas anotações. A transcrição fica armazenada localmente em minha máquina e não é compartilhada externamente. Caso prefiram, posso desativar agora."

**Inglês (cliente internacional):**
> "Before we start, I'd like to let you know I use a local transcription tool to support my notes. The transcript stays on my machine and isn't shared. If you'd rather I turn it off, just let me know."

---

## 7. Checklist antes do primeiro uso em ambiente real

- [ ] Li a política de gravação da Procurement Garage
- [ ] Se necessário, validei com RH/jurídico
- [ ] Defini disclosure default (com aviso / sem aviso) baseado em tipo de reunião
- [ ] Configurei retenção apropriada (não guardar pra sempre por default)
- [ ] Testei a ferramenta em 1-2 calls baixo risco antes de usar em call importante
- [ ] Sei como deletar transcripts individuais se alguém pedir
- [ ] Defini se vou comunicar à equipe que tenho essa ferramenta
