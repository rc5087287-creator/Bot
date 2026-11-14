# 🤖 Bot de Discord

Bot completo em Python (discord.py 2.x) com comandos de **prefixo (`#`)** e **barra (`/`)**.

## Instalação

1. Python 3.10 ou superior.
2. `pip install -r requirements.txt`
3. Copie `.env.example` para `.env` e coloque seu token em `DISCORD_TOKEN`.
4. No [Developer Portal](https://discord.com/developers/applications) → Bot, ative as **Privileged Gateway Intents**: **Message Content Intent** e **Server Members Intent**.
5. Convide o bot com os escopos `bot` e `applications.commands` e permissões de administrador (ou as necessárias para moderação).
6. `python main.py`

> ⚠️ O token antigo estava escrito dentro do código. Se o arquivo antigo já foi compartilhado, **gere um token novo** no Developer Portal (Reset Token).

## Módulos

| Módulo | Comandos |
|---|---|
| 🏠 Geral | `ajuda`, `ping`, `hello`, `botinfo`, `avatar`, `userinfo`, `serverinfo` |
| 🎉 Diversão | `d20`, `d5`, `dado 2d6+3`, `flip`, `8ball`, `escolher`, `ppt` (jogo com botões), `heh`, `emoji`, `meme`, `dog`, `cat`, `wifu`, `wifu1` |
| 🛠️ Utilidades | `calc`, `senha`, `enquete`, `sorteio`, `lembrar`, `lembretes`, `cancelarlembrete` |
| ⭐ Níveis | `xp`, `rank`, `setxp`, `resetxp`, `cargonivel adicionar/remover/listar` |
| 🛡️ Moderação | `kick`, `ban`, `unban`, `timeout`, `untimeout`, `limpar`, `slowmode`, `lock`, `unlock`, `warn`, `warns`, `delwarn`, `clearwarns` |
| ⚙️ Configuração | `config ver`, `config canal`, `config mensagem`, `config autocargo`, `config anunciarnivel` |
| 👑 Dono (ocultos) | `sync`, `reload`, `desligar`, `importarxp` |

Também inclui: boas-vindas/despedida, cargo automático, logs (mensagens apagadas/editadas, entradas, saídas, bans), tratamento de erros amigável, cooldowns, status rotativo e arquivo de log em `logs/bot.log`.

## Configuração rápida no servidor

```
/config canal tipo:logs canal:#logs
/config canal tipo:boasvindas canal:#boas-vindas
/config autocargo cargo:@Membro
/cargonivel adicionar nivel:5 cargo:@Veterano
```

Mensagens personalizadas aceitam `{membro}`, `{nome}`, `{servidor}` e `{contagem}`:
`/config mensagem tipo:boasvindas texto:Fala {membro}! Você é o {contagem}º do {servidor}!`

## Migrando o XP antigo

O XP agora é **por servidor** e fica em SQLite (`data/bot.db`). Para trazer o `xp.json` antigo, copiado em `data/xp_antigo.json`, rode no servidor desejado: `#importarxp` (só o dono do bot).

## Estrutura

```
main.py            # inicia o bot
bot/client.py      # classe do bot, banco, sessão HTTP
bot/config.py      # configurações (XP, cores, caminhos)
bot/database.py    # SQLite assíncrono
bot/cogs/          # módulos de comandos
bot/utils/         # funções auxiliares
bot_images/        # memes do comando meme (é só colocar imagens aqui)
```

Ajuste o ganho de XP e o cooldown em `bot/config.py`.
