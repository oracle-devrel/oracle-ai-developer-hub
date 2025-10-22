package dev.victormartin.oci.genai.backend.backend.data;

import java.util.List;

import org.springframework.data.jpa.repository.JpaRepository;

public interface MessageRepository extends JpaRepository<Message, String> {

  // Bounded fetch for latest messages in a conversation, newest first
  List<Message> findTop20ByConversationIdOrderByCreatedAtDesc(String conversationId);
}
