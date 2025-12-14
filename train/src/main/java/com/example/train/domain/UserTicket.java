package com.example.train.domain;

import jakarta.persistence.*;
import lombok.*;

import java.time.LocalDateTime;

@Entity
@Table(name = "user_tickets")
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class UserTicket {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    /** 유저 ID (지금은 1만 사용) */
    @Column(name = "user_id", nullable = false)
    private Long userId;

    /** 한 번의 여행(메뚜기 포함)을 묶어주는 ticketId */
    @Column(name = "ticket_id", nullable = false)
    private Long ticketId;

    /** 메뚜기 여부 */
    @Column(name = "is_hopper", nullable = false)
    private boolean hopper;

    /** 출발역 이름 */
    @Column(name = "origin_station", nullable = false)
    private String originStation;

    /** 도착역 이름 */
    @Column(name = "dest_station", nullable = false)
    private String destStation;

    /** 출발 일시 */
    @Column(name = "departure_time", nullable = false)
    private LocalDateTime departureTime;

    /** 도착 일시 */
    @Column(name = "arrival_time", nullable = false)
    private LocalDateTime arrivalTime;

    /** 기차 이름 (KTX xxx 등) */
    @Column(name = "train_no", nullable = false)
    private String trainNo;

    /** 호차 번호 */
    @Column(name = "car_no", nullable = false)
    private int carNo;

    /** 좌석 코드 (예: 7D) */
    @Column(name = "seat_code", nullable = false)
    private String seatCode;
}
