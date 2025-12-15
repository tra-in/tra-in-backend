package com.example.train.repository;

import com.example.train.domain.UserPick;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Collection;
import java.util.List;

public interface UserPickRepository extends JpaRepository<UserPick, Long> {

    // 중복 체크용: 같은 userTicketId에서 contentId가 이미 있나?
    List<UserPick> findByUserTicketIdAndContentIdIn(Long userTicketId, Collection<String> contentIds);
}
