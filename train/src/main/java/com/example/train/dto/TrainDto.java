package com.example.ticket.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;

@Data
@Builder
@AllArgsConstructor
public class TrainDto {
    private Long id;
    private String trainNo;
    private String trainType;
    private String origin;
    private String dest;
    private String departureTime; // ISO 문자열
    private String arrivalTime;
}
