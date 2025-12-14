package com.example.train.dto;

import com.example.train.domain.UserTicket;
import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;
import java.time.format.DateTimeFormatter;
import java.util.List;

@Data
public class UserTicketDto {

    /** JSON: { "userId": 1, ... } */
    @JsonProperty("userId")
    private Long userId;

    /** JSON: { "isHopper": true/false } */
    @JsonProperty("isHopper")
    private boolean hopper;

    /** 여러 구간(leg) 정보 */
    @JsonProperty("legs")
    private List<LegDto> legs;

    @Data
    public static class LegDto {

        @JsonProperty("originStation")
        private String originStation;

        @JsonProperty("destStation")
        private String destStation;

        // "2025-12-16T06:30:00" 같은 ISO 형식 문자열
        @JsonProperty("departureTime")
        private String departureTime;

        // "2025-12-16T07:25:00"
        @JsonProperty("arrivalTime")
        private String arrivalTime;

        @JsonProperty("trainNo")
        private String trainNo;

        @JsonProperty("carNo")
        private int carNo;

        @JsonProperty("seatCode")
        private String seatCode;
    }

    // UserTicket -> LegDto 변환
    public static LegDto toDto(UserTicket ticket) {
        LegDto dto = new LegDto();
        dto.setOriginStation(ticket.getOriginStation());
        dto.setDestStation(ticket.getDestStation());
        dto.setDepartureTime(ticket.getDepartureTime().toString());
        dto.setArrivalTime(ticket.getArrivalTime().toString());
        dto.setTrainNo(ticket.getTrainNo());
        dto.setCarNo(ticket.getCarNo());
        dto.setSeatCode(ticket.getSeatCode());
        return dto;
    }
}
