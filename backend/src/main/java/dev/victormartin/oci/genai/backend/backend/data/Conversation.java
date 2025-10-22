package dev.victormartin.oci.genai.backend.backend.data;

import java.time.OffsetDateTime;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

@Entity
@Table(name = "CONVERSATIONS")
public class Conversation {

  @Id
  @Column(name = "CONVERSATION_ID", length = 64, nullable = false)
  private String conversationId;

  @Column(name = "TENANT_ID", length = 64, nullable = false)
  private String tenantId;

  @Column(name = "USER_ID", length = 128)
  private String userId;

  // Let DB default populate; not set from JPA
  @Column(name = "CREATED_AT", insertable = false, updatable = false)
  private OffsetDateTime createdAt;

  @Column(name = "STATUS", length = 32)
  private String status;

  public Conversation() {}

  public Conversation(String conversationId, String tenantId, String userId, String status) {
    this.conversationId = conversationId;
    this.tenantId = tenantId;
    this.userId = userId;
    this.status = status;
  }

  public String getConversationId() {
    return conversationId;
  }

  public void setConversationId(String conversationId) {
    this.conversationId = conversationId;
  }

  public String getTenantId() {
    return tenantId;
  }

  public void setTenantId(String tenantId) {
    this.tenantId = tenantId;
  }

  public String getUserId() {
    return userId;
  }

  public void setUserId(String userId) {
    this.userId = userId;
  }

  public OffsetDateTime getCreatedAt() {
    return createdAt;
  }

  public String getStatus() {
    return status;
  }

  public void setStatus(String status) {
    this.status = status;
  }
}
