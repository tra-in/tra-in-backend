package com.example.train.dto;

import com.example.train.domain.UserTicket;
import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;

import java.util.List;

@Data
public class UserTicketDto {

    @JsonProperty("userId")
    private Long userId;

    // ✅ 추가: 프론트에서 trip.ticketId로 쓰는 값
    @JsonProperty("ticketId")
    private Long ticketId;

    @JsonProperty("isHopper")
    private boolean hopper;

    @JsonProperty("legs")
    private List<LegDto> legs;

    @Data
    public static class LegDto {
        @JsonProperty("originStation")
        private String originStation;

        @JsonProperty("destStation")
        private String destStation;

        @JsonProperty("departureTime")
        private String departureTime;

        @JsonProperty("arrivalTime")
        private String arrivalTime;

        @JsonProperty("trainNo")
        private String trainNo;

        @JsonProperty("carNo")
        private int carNo;

        @JsonProperty("seatCode")
        private String seatCode;
    }

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
