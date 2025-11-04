package dev.victormartin.oci.genai.backend.backend;

import javax.sql.DataSource;

import org.junit.jupiter.api.Test;
import org.mockito.Mockito;
import org.springframework.boot.SpringBootConfiguration;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Primary;
import org.springframework.test.context.ActiveProfiles;

import dev.victormartin.oci.genai.backend.backend.data.InteractionRepository;
import dev.victormartin.oci.genai.backend.backend.service.GenAiClientService;
import dev.victormartin.oci.genai.backend.backend.service.GenAiInferenceClientService;
import dev.victormartin.oci.genai.backend.backend.service.OCIGenAIService;

@ActiveProfiles("test")
@SpringBootTest(
  classes = {
    BackendApplicationTests.MinimalApp.class,
    BackendApplicationTests.TestMocks.class
  },
  webEnvironment = SpringBootTest.WebEnvironment.NONE,
  properties = "spring.main.lazy-initialization=true"
)
class BackendApplicationTests {

  @SpringBootConfiguration
  static class MinimalApp {}

  // Provide lightweight test doubles without using @MockBean (deprecated in Boot 3.5)
  @TestConfiguration
  static class TestMocks {
    @Bean
    @Primary
    GenAiInferenceClientService genAiInferenceClientService() {
      return Mockito.mock(GenAiInferenceClientService.class);
    }

    @Bean
    @Primary
    OCIGenAIService ociGenAIService() {
      return Mockito.mock(OCIGenAIService.class);
    }

    @Bean
    @Primary
    GenAiClientService genAiClientService() {
      return Mockito.mock(GenAiClientService.class);
    }

    @Bean
    @Primary
    InteractionRepository interactionRepository() {
      return Mockito.mock(InteractionRepository.class);
    }

    @Bean
    @Primary
    DataSource dataSource() {
      return Mockito.mock(DataSource.class);
    }
  }

  @Test
  void contextLoads() {
    // Context should load without connecting to Oracle DB or OCI
  }
}
