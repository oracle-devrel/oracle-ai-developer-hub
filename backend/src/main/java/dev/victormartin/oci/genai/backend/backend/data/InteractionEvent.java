package dev.victormartin.oci.genai.backend.backend.data;

import java.math.BigDecimal;
import java.time.OffsetDateTime;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

@Entity
@Table(name = "INTERACTIONS")
public class InteractionEvent {

  @Id
  @GeneratedValue(strategy = GenerationType.IDENTITY)
  @Column(name = "ID", nullable = false)
  private Long id;

  @Column(name = "TENANT_ID", length = 64)
  private String tenantId;

  @Column(name = "ROUTE", length = 64)
  private String route;

  @Column(name = "MODEL_ID", length = 255)
  private String modelId;

  // Store JSON as text via JPA; DB column type is JSON
  @Column(name = "PARAMS_JSON", columnDefinition = "CLOB")
  private String paramsJson;

  @Column(name = "LATENCY_MS")
  private Long latencyMs;

  @Column(name = "TOKENS_IN")
  private Long tokensIn;

  @Column(name = "TOKENS_OUT")
  private Long tokensOut;

  @Column(name = "COST_EST")
  private BigDecimal costEst;

  // Let DB default populate; not set from JPA
  @Column(name = "CREATED_AT", insertable = false, updatable = false)
  private OffsetDateTime createdAt;

  public InteractionEvent() {}

  public InteractionEvent(String tenantId, String route, String modelId) {
    this.tenantId = tenantId;
    this.route = route;
    this.modelId = modelId;
  }

  public Long getId() {
    return id;
  }

  public String getTenantId() {
    return tenantId;
  }

  public void setTenantId(String tenantId) {
    this.tenantId = tenantId;
  }

  public String getRoute() {
    return route;
  }

  public void setRoute(String route) {
    this.route = route;
  }

  public String getModelId() {
    return modelId;
  }

  public void setModelId(String modelId) {
    this.modelId = modelId;
  }

  public String getParamsJson() {
    return paramsJson;
  }

  public void setParamsJson(String paramsJson) {
    this.paramsJson = paramsJson;
  }

  public Long getLatencyMs() {
    return latencyMs;
  }

  public void setLatencyMs(Long latencyMs) {
    this.latencyMs = latencyMs;
  }

  public Long getTokensIn() {
    return tokensIn;
  }

  public void setTokensIn(Long tokensIn) {
    this.tokensIn = tokensIn;
  }

  public Long getTokensOut() {
    return tokensOut;
  }

  public void setTokensOut(Long tokensOut) {
    this.tokensOut = tokensOut;
  }

  public BigDecimal getCostEst() {
    return costEst;
  }

  public void setCostEst(BigDecimal costEst) {
    this.costEst = costEst;
  }

  public OffsetDateTime getCreatedAt() {
    return createdAt;
  }
}
