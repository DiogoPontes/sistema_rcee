### AXON — Plataforma de Inteligência Estratégica em Rede

Descrição
---------
AXON é uma plataforma distribuída para curadoria, validação e publicação de conteúdo estratégico em rede. O sistema é composto por três aplicações independentes, cada uma com sua própria base de dados:

- Cadastro — ponto de entrada (writers). Qualquer usuário com permissão pode criar um rascunho e submeter uma sugestão de publicação.
- Admin — ambiente de moderação e edição (editors). Gestores avaliam as sugestões, editam, aprovam ou reprovam conteúdos.
- Consulta — base de leitura pública (readers). Exibe para todos os usuários os conteúdos aprovados pelo Admin.

Princípio arquitetural
----------------------
A separação clara entre escrita (Cadastro / Admin) e leitura (Consulta) garante desacoplamento, escalabilidade e melhor performance para consultas. A sincronização entre serviços é feita de forma assíncrona via Kafka (event-driven).

Fluxo de publicação (resumido)
------------------------------
1. Usuário cria rascunho no **Cadastro** e solicita aprovação.
2. O gestor abre o **Admin**, visualiza o rascunho, edita se necessário e aprova ou reprova.
3. Ao aprovar, o **Admin** publica um evento Kafka (`full_sync` / `status_update`) contendo os dados do post.
4. O **Consulta** consome os eventos e realiza um upsert (INSERT/UPDATE) ou remoção, tornando a informação disponível para todos.

Eventos Kafka (exemplos)
------------------------
- `full_sync` — contém todos os campos do post (id, title, body, assets, category, status, timestamps). Usado para sincronização completa.
- `status_update` — sinaliza mudanças de status (`approved`, `disapproved`, `published`, etc.). Pode ser leve (só status) ou conter dados parciais.

Comportamento esperado no consumer (Consulta)
---------------------------------------------
- Receber `full_sync` com `status == "approved"` → realizar upsert (criar/atualizar) no banco de consulta e baixar assets referenciados.
- Receber `status_update` com reprovação → excluir post e assets da base de consulta.
- Evitar remoções baseadas em eventos intermediários; preferir `full_sync` para upsert confiável.

Deploy (desenvolvimento)
------------------------
Pré-requisitos: Docker & Docker Compose.

Subir todo o ambiente:
```bash
docker compose up --build -d
