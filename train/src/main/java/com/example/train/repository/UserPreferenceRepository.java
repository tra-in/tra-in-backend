package com.example.train.repository;

import com.example.train.domain.UserPreference;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;

public interface UserPreferenceRepository extends JpaRepository<UserPreference, Long> {
    Optional<UserPreference> findByUserIdAndTicketId(Long userId, Long ticketId);
}
