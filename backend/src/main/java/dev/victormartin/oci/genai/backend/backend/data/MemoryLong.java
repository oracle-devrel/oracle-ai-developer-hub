package dev.victormartin.oci.genai.backend.backend.data;

import java.time.OffsetDateTime;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

@Entity
@Table(name = "MEMORY_LONG")
public class MemoryLong {

  @Id
  @Column(name = "CONVERSATION_ID", length = 64, nullable = false)
  private String conversationId;

  @Column(name = "SUMMARY_TEXT", columnDefinition = "CLOB")
  private String summaryText;

  // DB default should populate; not set from JPA
  @Column(name = "UPDATED_AT", insertable = false, updatable = false)
  private OffsetDateTime updatedAt;

  public MemoryLong() {}

  public MemoryLong(String conversationId, String summaryText) {
    this.conversationId = conversationId;
    this.summaryText = summaryText;
  }

  public String getConversationId() {
    return conversationId;
  }

  public void setConversationId(String conversationId) {
    this.conversationId = conversationId;
  }

  public String getSummaryText() {
    return summaryText;
  }

  public void setSummaryText(String summaryText) {
    this.summaryText = summaryText;
  }

  public OffsetDateTime getUpdatedAt() {
    return updatedAt;
  }
}
