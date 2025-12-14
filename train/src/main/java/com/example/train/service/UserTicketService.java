package com.example.train.service;

import com.example.train.domain.UserTicket;
import com.example.train.dto.UserTicketDto;
import com.example.train.repository.UserTicketRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;

@Service
@RequiredArgsConstructor
public class UserTicketService {

    private final UserTicketRepository userTicketRepository;

    // "2025-12-16T06:30:00" 형식
    private static final DateTimeFormatter ISO_FMT = DateTimeFormatter.ISO_LOCAL_DATE_TIME;

    @Transactional
    public void createTickets(UserTicketDto request) {
        Long userId = request.getUserId();
        boolean isHopper = request.isHopper();

        // 기존 ticketId 최댓값 + 1 -> 새 여행 번호
        Long maxTicketId = userTicketRepository.findMaxTicketIdByUserId(userId);
        long newTicketId = (maxTicketId == null ? 0L : maxTicketId) + 1L;

        for (UserTicketDto.LegDto leg : request.getLegs()) {
            LocalDateTime depart = LocalDateTime.parse(leg.getDepartureTime(), ISO_FMT);
            LocalDateTime arrive = LocalDateTime.parse(leg.getArrivalTime(), ISO_FMT);

            UserTicket ticket = UserTicket.builder()
                    .userId(userId)
                    .ticketId(newTicketId)
                    .hopper(isHopper)
                    .originStation(leg.getOriginStation())
                    .destStation(leg.getDestStation())
                    .departureTime(depart)
                    .arrivalTime(arrive)
                    .trainNo(leg.getTrainNo())
                    .carNo(leg.getCarNo())
                    .seatCode(leg.getSeatCode())
                    .build();

            userTicketRepository.save(ticket);
        }
    }
}
