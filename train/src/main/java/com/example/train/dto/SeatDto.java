package com.example.ticket.dto;

import lombok.AllArgsConstructor;
import lombok.Data;

@Data
@AllArgsConstructor
public class SeatDto {
    private Long id;
    private Integer rowNo;
    private String col;
    private String seatCode;
    private String status; // "AVAILABLE" / "SOLD"
}
