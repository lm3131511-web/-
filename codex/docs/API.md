# API

`POST /risk`

Request body:
```
{
  "features": { ... DeterministicFeatures ... },
  "sentiment": { ... AggregatedSentiment ... },
  "meta": { ... MetaContext ... }
}
```

Response: `RiskAssessment` JSON adhering to `prompts/schemas/llm_risk_assessment.schema.json`.
