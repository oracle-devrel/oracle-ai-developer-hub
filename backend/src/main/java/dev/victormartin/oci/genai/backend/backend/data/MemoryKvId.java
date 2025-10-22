package dev.victormartin.oci.genai.backend.backend.data;

import java.io.Serializable;
import java.util.Objects;

public class MemoryKvId implements Serializable {
  private String conversationId;
  private String key;

  public MemoryKvId() {}

  public MemoryKvId(String conversationId, String key) {
    this.conversationId = conversationId;
    this.key = key;
  }

  public String getConversationId() {
    return conversationId;
  }

  public String getKey() {
    return key;
  }

  @Override
  public boolean equals(Object o) {
    if (this == o) return true;
    if (!(o instanceof MemoryKvId)) return false;
    MemoryKvId that = (MemoryKvId) o;
    return Objects.equals(conversationId, that.conversationId) &&
           Objects.equals(key, that.key);
  }

  @Override
  public int hashCode() {
    return Objects.hash(conversationId, key);
  }
}
