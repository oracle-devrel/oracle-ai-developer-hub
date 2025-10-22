package dev.victormartin.oci.genai.backend.backend.data;

import org.springframework.data.jpa.repository.JpaRepository;

public interface InteractionEventRepository extends JpaRepository<InteractionEvent, Long> {
}
