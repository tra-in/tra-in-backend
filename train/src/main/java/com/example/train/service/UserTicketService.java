package com.example.train.service;

import com.example.train.domain.UserTicket;
import com.example.train.dto.UserTicketDto;
import com.example.train.repository.UserTicketRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class UserTicketService {

    private final UserTicketRepository userTicketRepository;
    private static final DateTimeFormatter ISO_FMT = DateTimeFormatter.ISO_LOCAL_DATE_TIME;

    @Transactional
    public void createTickets(UserTicketDto request) {
        Long userId = request.getUserId();
        boolean isHopper = request.isHopper();

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

    // 반환 타입 List<UserTicketDto>로 변경!
    public List<UserTicketDto> getUserTicketsByUserId(Long userId) {
        // 1. 엔티티 조회
        List<UserTicket> tickets = userTicketRepository.findByUserId(userId);

        // 2. ticketId별로 그룹화
        Map<Long, List<UserTicket>> grouped = tickets.stream()
                .collect(Collectors.groupingBy(UserTicket::getTicketId));

        // 3. DTO로 변환
        List<UserTicketDto> result = new ArrayList<>();

        for (Map.Entry<Long, List<UserTicket>> entry : grouped.entrySet()) {
            List<UserTicket> legs = entry.getValue();
            if (legs.isEmpty()) continue;

            UserTicket first = legs.get(0);

            UserTicketDto dto = new UserTicketDto();
            dto.setUserId(first.getUserId());
            dto.setHopper(first.isHopper());
            dto.setLegs(legs.stream()
                    .map(UserTicketDto::toDto)
                    .collect(Collectors.toList()));

            result.add(dto);
        }

        return result;
    }

    public UserTicketDto getLatestTripForMain(Long userId) {

        Long latestTicketId = userTicketRepository.findMaxTicketIdByUserId(userId);
        if (latestTicketId == null) return null;

        // 최신 예매
        List<UserTicket> latestLegs =
                userTicketRepository.findByUserIdAndTicketId(userId, latestTicketId);
        if (latestLegs.isEmpty()) return null;

        boolean isHopper = latestLegs.get(0).isHopper();

        List<UserTicket> allLegs = new ArrayList<>();

        if (isHopper) {
            // 이전 ticket (출발 → 경유)
            Long prevTicketId = latestTicketId - 1;
            List<UserTicket> prevLegs =
                    userTicketRepository.findByUserIdAndTicketId(userId, prevTicketId);

            allLegs.addAll(prevLegs);
        }

        // 최신 ticket (경유 → 도착)
        allLegs.addAll(latestLegs);

        // 출발 시간 기준 정렬
        allLegs.sort(Comparator.comparing(UserTicket::getDepartureTime));

        UserTicket first = allLegs.get(0);

        UserTicketDto dto = new UserTicketDto();
        dto.setUserId(first.getUserId());
        dto.setHopper(isHopper);
        dto.setLegs(
                allLegs.stream()
                        .map(UserTicketDto::toDto)
                        .toList()
        );

        return dto;
    }


}