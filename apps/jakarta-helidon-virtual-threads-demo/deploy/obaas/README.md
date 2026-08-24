# OBaaS deployment

This guide deploys the Helidon credit-decision service used by the virtual-thread demos. It assumes an OBaaS environment that provides Kubernetes, APISIX, Oracle Autonomous Database, OpenTelemetry injection, and SigNoz.

## Configure the values file

Update these deployment-specific fields in `helidon-credit-service/values-obaas.yaml` before deploying:

- `image.repository` and `image.tag`
- `obaas.releaseName`
- `database.authN.secretName`
- `database.walletSecret`

The application keeps database settings out of source code. OBaaS injects the datasource configuration and credentials. The service uses Helidon Data, Jakarta Persistence, and Oracle JDBC for the persisted credit-decision path.

## Build and push the image

From the repository root:

```bash
cd helidon-credit-service
mvn clean package k8s:build k8s:push \
  -Dimage.registry=<your-ocir-registry> \
  -Dimage.tag=1.0.0-SNAPSHOT
cd ..
```

If Rancher Desktop provides the Docker daemon, set its socket before invoking Maven:

```bash
export DOCKER_HOST=unix:///Users/$USER/.rd/docker.sock
```

## Deploy

Set the chart location and namespace for your environment:

```bash
export OBAAS_CHART=<path-to-obaas-sample-app>
export NAMESPACE=obaas
```

Deploy or upgrade the service:

```bash
helm upgrade --install helidon-credit-service "$OBAAS_CHART" \
  -f helidon-credit-service/values-obaas.yaml \
  -n "$NAMESPACE"
```

Verify it started with the Oracle-backed repository:

```bash
kubectl get pods -n "$NAMESPACE" -l app.kubernetes.io/instance=helidon-credit-service
kubectl logs -n "$NAMESPACE" deploy/helidon-credit-service --tail=100
```

The startup log should report that Oracle JDBC persistence and the Helidon Data repository are available.

## Expose through APISIX

Port-forward the APISIX Admin API:

```bash
export OBAAS_RELEASE=obaas
export APISIX_ADMIN_PORT=19180

kubectl port-forward -n "$NAMESPACE" \
  "svc/${OBAAS_RELEASE}-apisix-admin" \
  "${APISIX_ADMIN_PORT}:9180"
```

In another terminal, derive the APISIX admin key and create the service routes:

```bash
export SERVICE_NAME="${NAMESPACE}/helidon-credit-service:http"

CONFIG_YAML=$(kubectl get configmap "${OBAAS_RELEASE}-apisix" \
  -n "$NAMESPACE" \
  -o jsonpath='{.data.config\.yaml}')

ADMIN_KEY=$(printf '%s\n' "$CONFIG_YAML" | \
  awk '/name: *"admin"|name: *admin/{found=1; next} found && /key:/{gsub(/"|\047/, "", $2); print $2; exit}')

curl --noproxy '*' -s "http://127.0.0.1:${APISIX_ADMIN_PORT}/apisix/admin/routes/1200" \
  -H "X-API-KEY: ${ADMIN_KEY}" \
  -H 'Content-Type: application/json' \
  -X PUT \
  -d "{
    \"name\": \"helidon-credit-decisions\",
    \"uri\": \"/credit-decisions*\",
    \"methods\": [\"GET\", \"POST\", \"OPTIONS\"],
    \"upstream\": {
      \"service_name\": \"${SERVICE_NAME}\",
      \"type\": \"roundrobin\",
      \"discovery_type\": \"kubernetes\"
    },
    \"plugins\": {
      \"opentelemetry\": {\"sampler\": {\"name\": \"always_on\"}},
      \"prometheus\": {\"prefer_name\": true}
    }
  }"

curl --noproxy '*' -s "http://127.0.0.1:${APISIX_ADMIN_PORT}/apisix/admin/routes/1201" \
  -H "X-API-KEY: ${ADMIN_KEY}" \
  -H 'Content-Type: application/json' \
  -X PUT \
  -d "{
    \"name\": \"helidon-credit-health\",
    \"uri\": \"/health*\",
    \"methods\": [\"GET\", \"HEAD\", \"OPTIONS\"],
    \"upstream\": {
      \"service_name\": \"${SERVICE_NAME}\",
      \"type\": \"roundrobin\",
      \"discovery_type\": \"kubernetes\"
    },
    \"plugins\": {
      \"opentelemetry\": {\"sampler\": {\"name\": \"always_on\"}},
      \"prometheus\": {\"prefer_name\": true}
    }
  }"
```

Set `GATEWAY_URL` to the public APISIX address and verify the service:

```bash
export GATEWAY_URL=http://<gateway-address>
curl -s "$GATEWAY_URL/health/simple" | jq
curl -s -X POST "$GATEWAY_URL/credit-decisions" \
  -H 'content-type: application/json' \
  -d @api/sample-requests/approved.json | jq
```

## SigNoz access

Retrieve the SigNoz account from the OBaaS namespace. On macOS use `base64 -D`; on Linux use `base64 -d`.

```bash
kubectl get secret signoz-authn -n "$NAMESPACE" \
  -o jsonpath='{.data.email}' | base64 -D; echo

kubectl get secret signoz-authn -n "$NAMESPACE" \
  -o jsonpath='{.data.password}' | base64 -D; echo
```

Use the Helidon JVM Details dashboard for request rate and virtual-thread signals. Use the Oracle dashboard to correlate user commits and database wait activity with the DB-backed k6 run.
