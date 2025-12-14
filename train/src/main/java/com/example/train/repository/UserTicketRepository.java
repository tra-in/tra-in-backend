package com.example.train.repository;

import com.example.train.domain.UserTicket;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface UserTicketRepository extends JpaRepository<UserTicket, Long> {

    /**
     * 해당 유저가 가진 ticketId 중 최댓값 (없으면 null)
     */
    @Query("select max(ut.ticketId) from UserTicket ut where ut.userId = :userId")
    Long findMaxTicketIdByUserId(@Param("userId") Long userId);
}
