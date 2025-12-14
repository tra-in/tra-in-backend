package com.example.train.repository;

import com.example.train.domain.Train;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

import java.time.LocalDateTime;
import java.util.List;

public interface TrainRepository extends JpaRepository<Train, Long> {

    @Query("""
        SELECT t FROM Train t
        WHERE t.originStation.name = :originName
          AND t.destStation.name = :destName
          AND t.departureTime >= :start
          AND t.departureTime < :end
        ORDER BY t.departureTime
        """)
    List<Train> searchTrains(
            String originName,
            String destName,
            LocalDateTime start,
            LocalDateTime end
    );
}
