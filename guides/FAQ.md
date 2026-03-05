# FAQ

This FAQ builds on TROUBLESHOOTING.md by providing quick answers to common questions in a modular Q&A format. It covers deployment, configuration, and usage, with steps for verification. For detailed debugging, see TROUBLESHOOTING.md; for setup, start with LOCAL.md.

## Deployment and Access

Q: How do I get the Load Balancer Public IP address?  
A: Use this command to retrieve the IP for accessing the app on OKE:  
```bash
kubectl get service -n ingress-nginx -o jsonpath='{.items[?(@.spec.type=="LoadBalancer")].status.loadBalancer.ingress[0].ip}'
```  
Step 1: Ensure kubectl is configured (see K8S.md). Step 2: If no IP, wait for provisioning. Step 3: Access http://<IP>.

Q: How do I get the dockerconfigjson from the secret?  
A: Extract the config for OCIR authentication:  
```bash
kubectl get secret ocir-secret --output="jsonpath={.data.\.dockerconfigjson}" | base64 --decode | jq
```  
Step 1: Run in the namespace with the secret. Step 2: Use the output for docker login. See K8S.md for OCIR setup.

## Configuration and Models

Q: How do I list available models?  
A: Query the backend:  
```bash
curl http://localhost:8080/api/genai/models
```  
Example response (JSON):  
```json
[
  {"id": "ocid1.generativeaimodel.oc1....", "displayName": "cohere.command-r-plus", "vendor": "cohere", "capabilities": ["CHAT"]}
]
```  
Step 1: Ensure backend is running (LOCAL.md). Step 2: Filter by "CHAT" for chat models. See MODELS.md for details.

Q: What if my embedding dimension doesn't match the schema?  
A: The default is VECTOR(1024, FLOAT32). Step 1: Check your model in MODELS.md. Step 2: Update V2__kb_tables.sql in Liquibase. Step 3: Re-run migrations. Cross-reference RAG.md for ingestion.

## RAG and Data

Q: How do I verify KB ingestion after upload?  
A: Use diagnostics:  
```bash
curl http://localhost:8080/api/kb/diag?tenantId=default
```  
Example response:  
```json
{"dbOk": true, "chunksTenant": 5, "embeddingsNonNullTenant": 5}
```  
Step 1: Upload via /api/upload (RAG.md). Step 2: Check counts >0. Step 3: Test RAG query.

Q: Why is RAG returning "I don’t know"?  
A: Possible causes: empty KB or tenant mismatch. Step 1: Validate with /api/kb/diag. Step 2: Ensure same tenant for upload/query. Step 3: If vectors missing, fallback to text search (see TROUBLESHOOTING.md).

## Build and Development

Q: How do I build the app?  
A: For backend: `./gradlew clean build` (aligns with Spring Boot 3.2.x/Java 21 in build.gradle). For frontend: `npm ci && npm run build` (Oracle JET 19.x in package.json). See LOCAL.md for running, CHANGES.md for recent build fixes.

Q: How do I contribute?  
A: Follow CONTRIBUTING.md guidelines. Step 1: Fork and branch. Step 2: Make changes. Step 3: PR with description. Add to CHANGES.md.
