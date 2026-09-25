---
name: revisao-codigo
description: Aplique ao revisar o diff de uma entrega antes do PR. Formato de revisão com severidade e veredito, princípios gerais e onde ficam as regras específicas do projeto.
version: 1.0.0
author: Joao Pires
metadata:
  hermes:
    tags: [review, quality, qa]
---

# Revisão de código (antes do PR)

> Formato inspirado nos reviewers do `hypesoftlabs/tuple-workspace`
> (`angry-senior-reviewer`, `code-spanker`), sem o tom agressivo: direto e com fix.

Revise **o que mudou** (`git diff <base>...HEAD`, `detect_changes` da skill
`codebase-memory`), não o repo inteiro. Leia cada linha do diff.

## Regras que valem em qualquer projeto

1. **Simplicidade** — um júnior entende em 30 s? Abstração para uso único, classe
   onde bastava função, config que ninguém pediu → 🟡.
2. **Cada função faz o que o nome diz** — e só isso.
3. **Erros propagam** — `catch` que devolve `null`/engole erro é mentira para quem
   chamou → 🔴.
4. **Dado pesado no backend/banco** — filtrar/ordenar/agregar em memória o que o banco
   faz, N+1, `findMany`/listagem sem paginação → 🔴/🟡.
5. **Segurança** — todo endpoint verifica acesso (sem IDOR); input validado; nenhum
   segredo em código, log ou teste → 🔴.
6. **Testes** — teste novo para comportamento novo; **teste existente enfraquecido**
   (asserção removida, `skip`, deletado) sem autorização explícita → 🔴.
7. **Mudança cirúrgica** — linha que não se liga à issue (refactor vizinho,
   formatação alheia) → 🟠 (skill `karpathy-guidelines`).

**Regras específicas do projeto** (stack, padrões, "nunca faça X aqui") ficam no
`.kiro/steering/` do projeto — leia antes de revisar e aplique como regras de mesma força.

## Formato

```markdown
## Revisão — <issue KEY> · <resumo>

### Avaliação geral
<um parágrafo honesto>

### Achados
[🔴|🟡|🟠] **<título>**
📍 <arquivo:linha>
❌ <o que está errado e qual regra viola>
✅ <como deve ficar — código ou abordagem concreta>

### Veredito
APROVADO ✅ · APROVADO COM RESSALVAS 🟡 · MUDANÇAS NECESSÁRIAS 🔴
```

🔴 CRÍTICO (quebrado, inseguro, arquitetura errada) · 🟡 AVISO (funciona mas é
feio/complexo demais) · 🟠 INCÔMODO (piora o código; corrigir antes do merge).

Veredito 🔴 → devolve ao dev com os achados. 🟡 → dev decide com o @techlead.
✅ → libera o PR. Código bom: diga que é bom, em uma linha.
