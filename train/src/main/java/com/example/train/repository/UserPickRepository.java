package com.example.train.repository;

import com.example.train.domain.UserPick;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;

public interface UserPickRepository extends JpaRepository<UserPick, Long> {

    List<UserPick> findByUserIdAndTicketId(Long userId, Long ticketId);

    List<UserPick> findByUserIdAndTicketIdAndExcludedTrue(Long userId, Long ticketId);

    Optional<UserPick> findByUserIdAndTicketIdAndContentId(
            Long userId, Long ticketId, Long contentId
    );
}
