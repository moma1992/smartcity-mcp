# <%¹ŞüÈ·Æ£ MCP µüĞü

<%nªü×óÇü¿’;(W_Model Context Protocol (MCP) µüĞügYClaude Desktop Jˆs Claude Code h#:Wf<%n¹ŞüÈ·Æ£Çü¿xn¢¯»¹’Ğ›W~Y

## _ı

### Ğ›Y‹Äüë

1. **get_yaizu_api_catalog**: <%nªü×óÇü¿API«¿í°’Ö—
2. **get_yaizu_city_data**: š«Æ´ên<%Çü¿’Ö—
3. **search_yaizu_facilities**: <%nlq½-’"

### Ğ›Y‹ê½ü¹

1. **yaizu://info**: <%nú,Å1
2. **yaizu://status**: MCPµüĞünÕ\¶Á

## »ÃÈ¢Ã×

### Å°ƒ

- Python 3.13.7 å

- uv 0.8.13 å


### ¤ó¹Èüë

```bash
# êİ¸Èên¯íüó
git clone <repository-url>
cd smartcity-mcp

# X¢Ân¤ó¹Èüë
uv sync

# °ƒ-šÅkÜXf	
cp .env.example .env
```

### Claude Desktop gn-š

1. Claude Desktop n-šÕ¡¤ëkå’ı :

```json
{
  "mcpServers": {
    "yaizu-smartcity": {
      "command": "uv",
      "args": [
        "--directory",
        "/ABSOLUTE/PATH/TO/smartcity-mcp",
        "run",
        "server.py"
      ]
    }
  }
}
```

2. `/ABSOLUTE/PATH/TO/smartcity-mcp` ’Ÿ›n×í¸§¯ÈÑ¹knMÛHfO`UD

## (¹Õ

### ‹zûÇĞÃ°

```bash
# MCP Inspector ’(W_ÇĞÃ°
uv run mcp dev server.py

# ô¥ŸL
uv run python server.py
```

### Claude Desktop gn)(

Claude Desktop ’wÕŒånˆFj×íó×ÈgÄüë’(gM~Y:

```
<%nAPI«¿í°’‹[fO`UD
```

```
<%nlq½-’"WfO`UD
```

```
<%nºãÇü¿’Ö—WfO`UD
```

## API ¨óÉİ¤óÈ

- ú,URL: `https://city-api-catalog-api.smartcity-pf.com/yaizu`
- <: Basic AuthenticationÅkÜXf	

## €SÕØ

- **Õìüàïü¯**: MCP Python SDK 1.13.1
- **HTTP ¯é¤¢óÈ**: httpx, aiohttp
- **^æ**: asyncio
- **í°**: Python–é¤Öéê

## é¤»ó¹

MIT License

## ¢.

Issues „ Pull Request ’SÎW~Y

## µİüÈ

OLLzW_4oå’ºWfO`UD:

1. Python h uv nĞü¸çó
2. X¢Ân¤ó¹Èüë¶Á
3. Claude Desktop n-š
4. ÍÃÈïü¯¥š

s0o CLAUDE.md ’ÂgWfO`UD