package com.example.ticket.repository;

import com.example.ticket.domain.Seat;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface SeatRepository extends JpaRepository<Seat, Long> {
    List<Seat> findByCarIdOrderByRowNoAscColAsc(Long carId);
}
