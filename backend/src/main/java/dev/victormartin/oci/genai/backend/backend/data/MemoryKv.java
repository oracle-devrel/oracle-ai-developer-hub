package dev.victormartin.oci.genai.backend.backend.data;

import java.time.OffsetDateTime;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.IdClass;
import jakarta.persistence.Table;

@Entity
@Table(name = "MEMORY_KV")
@IdClass(MemoryKvId.class)
public class MemoryKv {

  @Id
  @Column(name = "CONVERSATION_ID", length = 64, nullable = false)
  private String conversationId;

  @Id
  @Column(name = "KEY", length = 128, nullable = false)
  private String key;

  // Store as text; DB column is JSON. Using CLOB avoids driver-specific JSON mapping issues.
  @Column(name = "VALUE_JSON", columnDefinition = "CLOB")
  private String valueJson;

  @Column(name = "TTL_TS")
  private OffsetDateTime ttlTs;

  public MemoryKv() {}

  public MemoryKv(String conversationId, String key, String valueJson, OffsetDateTime ttlTs) {
    this.conversationId = conversationId;
    this.key = key;
    this.valueJson = valueJson;
    this.ttlTs = ttlTs;
  }

  public String getConversationId() {
    return conversationId;
  }

  public void setConversationId(String conversationId) {
    this.conversationId = conversationId;
  }

  public String getKey() {
    return key;
  }

  public void setKey(String key) {
    this.key = key;
  }

  public String getValueJson() {
    return valueJson;
  }

  public void setValueJson(String valueJson) {
    this.valueJson = valueJson;
  }

  public OffsetDateTime getTtlTs() {
    return ttlTs;
  }

  public void setTtlTs(OffsetDateTime ttlTs) {
    this.ttlTs = ttlTs;
  }
}
