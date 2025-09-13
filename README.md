# Telegram SMC Bot — Indicadores Extras + Toggles
Inclui todos os recursos anteriores e **novos indicadores**:
- **ATR(14)**
- **SuperTrend(10,3)** (linha e direção)
- **VWAP**
- (Já incluídos) RSI(9), MACD(6,13,4), StochRSI(8,5,5,3), KDJ(5,3,3), Parabolic SAR

## Como ligar/desligar indicadores no comando
```
/analisa <PAR> <TF> [on=lista] [off=lista]
```
Exemplos:
- `on=atr,supertrend` → força exibir ATR e SuperTrend
- `off=kdj,psar` → oculta KDJ e Parabolic SAR
Indicadores válidos: `rsi, macd, stochrsi, kdj, psar, atr, supertrend, vwap`.

## Push para seu GitHub (passos)
1. Crie um repositório vazio no GitHub.
2. No terminal, dentro da pasta do projeto:
   ```bash
   git init
   git add .
   git commit -m "telegram smc bot com indicadores extras e toggles"
   git branch -M main
   git remote add origin https://github.com/<seu-usuario>/<seu-repo>.git
   git push -u origin main
   ```
3. Configure no Render conforme instruções do README principal.
