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
            Long ticketId = entry.getKey();
            List<UserTicket> legs = entry.getValue();
            if (legs.isEmpty()) continue;

            UserTicket first = legs.get(0);

            UserTicketDto dto = new UserTicketDto();
            dto.setUserId(first.getUserId());
            dto.setTicketId(ticketId);
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

        List<UserTicket> latestLegs =
                userTicketRepository.findByUserIdAndTicketId(userId, latestTicketId);
        if (latestLegs.isEmpty()) return null;

        // ✅ 여기서 "한 번의 여행 묶음 ticketId"를 내려줘야 프론트가 trip.ticketId를 갖는다
        UserTicket first = latestLegs.get(0);

        UserTicketDto dto = new UserTicketDto();
        dto.setUserId(first.getUserId());
        dto.setTicketId(latestTicketId);      // ✅ 추가!!!
        dto.setHopper(first.isHopper());
        dto.setLegs(
                latestLegs.stream()
                        .sorted(Comparator.comparing(UserTicket::getDepartureTime))
                        .map(UserTicketDto::toDto)
                        .toList()
        );

        return dto;
    }

}