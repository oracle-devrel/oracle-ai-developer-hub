package dev.victormartin.oci.genai.backend.backend.data;

import java.time.OffsetDateTime;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

@Entity
@Table(name = "MESSAGES")
public class Message {

  @Id
  @Column(name = "MESSAGE_ID", length = 64, nullable = false)
  private String messageId;

  @Column(name = "CONVERSATION_ID", length = 64, nullable = false)
  private String conversationId;

  // Values: 'user','assistant','system' (DB constraint)
  @Column(name = "ROLE", length = 16)
  private String role;

  @Column(name = "CONTENT", columnDefinition = "CLOB")
  private String content;

  @Column(name = "TOKENS_IN")
  private Long tokensIn;

  @Column(name = "TOKENS_OUT")
  private Long tokensOut;

  // Let DB default populate; not set from JPA
  @Column(name = "CREATED_AT", insertable = false, updatable = false)
  private OffsetDateTime createdAt;

  public Message() {}

  public Message(String messageId, String conversationId, String role, String content) {
    this.messageId = messageId;
    this.conversationId = conversationId;
    this.role = role;
    this.content = content;
  }

  public String getMessageId() {
    return messageId;
  }

  public void setMessageId(String messageId) {
    this.messageId = messageId;
  }

  public String getConversationId() {
    return conversationId;
  }

  public void setConversationId(String conversationId) {
    this.conversationId = conversationId;
  }

  public String getRole() {
    return role;
  }

  public void setRole(String role) {
    this.role = role;
  }

  public String getContent() {
    return content;
  }

  public void setContent(String content) {
    this.content = content;
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

  public OffsetDateTime getCreatedAt() {
    return createdAt;
  }
}
