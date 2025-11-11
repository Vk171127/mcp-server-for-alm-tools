# Cost Monitoring for ALM Traceability MCP Server

## Current Configuration (Minimal Cost)

- **Service**: Google Cloud Run
- **Memory**: 256Mi
- **CPU**: 0.25 vCPU
- **Max Instances**: 1
- **Min Instances**: 0 (scales to zero)
- **Concurrency**: 1

## Expected Costs

- **Free Tier**: 2 million requests/month, 400,000 GB-seconds/month
- **Pay-per-use**: Only when requests are being processed
- **Idle Cost**: $0 (scales to zero)

## Monitoring Commands

```bash
# Check service status
gcloud run services describe alm-traceability-server --region=us-central1

# View logs
gcloud logs read "resource.type=cloud_run_revision AND resource.labels.service_name=alm-traceability-server" --limit=50

# Monitor usage
gcloud monitoring metrics list --filter="metric.type:run.googleapis.com"
```

## Optimization Notes

- Server scales to zero when not in use (no idle costs)
- Minimal resource allocation keeps per-request costs low
- In-memory storage (no database costs for demo)
- Single region deployment (us-central1)
