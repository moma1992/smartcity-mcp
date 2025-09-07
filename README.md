# <%���ȷƣ MCP ����

<%n��������;(W_Model Context Protocol (MCP) ����gYClaude Desktop J�s Claude Code h#:Wf<%n���ȷƣ���xn�����ЛW~Y

## _�

### ЛY����

1. **get_yaizu_api_catalog**: <%n�������API���֗
2. **get_yaizu_city_data**: ��ƴ�n<%����֗
3. **search_yaizu_facilities**: <%nlq�-�"

### ЛY����

1. **yaizu://info**: <%n�,�1
2. **yaizu://status**: MCP����n�\��

## ��Ȣ��

### Ł��

- Python 3.13.7 �

- uv 0.8.13 �


### �����

```bash
# �ݸ��n����
git clone <repository-url>
cd smartcity-mcp

# �X��n�����
uv sync

# ��-�Łk�Xf	
cp .env.example .env
```

### Claude Desktop gn-�

1. Claude Desktop n-�ա��k����:

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

2. `/ABSOLUTE/PATH/TO/smartcity-mcp` ���n����ѹknM�HfO`UD

## (��

### �z���ð

```bash
# MCP Inspector �(W_��ð
uv run mcp dev server.py

# ���L
uv run python server.py
```

### Claude Desktop gn)(

Claude Desktop ��wՌ�n�Fj�����g���(gM~Y:

```
<%nAPI����[fO`UD
```

```
<%nlq�-�"WfO`UD
```

```
<%n������֗WfO`UD
```

## API ���ݤ��

- �,URL: `https://city-api-catalog-api.smartcity-pf.com/yaizu`
- �<: Basic AuthenticationŁk�Xf	

## �S��

- **�������**: MCP Python SDK 1.13.1
- **HTTP �餢��**: httpx, aiohttp
- **^�**: asyncio
- **�**: Python�����

## 餻�

MIT License

## �.

Issues � Pull Request �S�W~Y

## ����

OLLzW_4o����WfO`UD:

1. Python h uv n�����
2. �X��n������
3. Claude Desktop n-�
4. ��������

s0o CLAUDE.md ��gWfO`UD