package dev.victormartin.oci.genai.backend.backend.data;

import java.time.OffsetDateTime;
import java.util.Optional;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.transaction.annotation.Transactional;

public interface MemoryKvRepository extends JpaRepository<MemoryKv, MemoryKvId> {

  Optional<MemoryKv> findByConversationIdAndKey(String conversationId, String key);

  @Modifying
  @Transactional
  int deleteByTtlTsBefore(OffsetDateTime ts);
}
