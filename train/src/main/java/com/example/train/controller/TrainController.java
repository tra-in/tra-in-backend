package com.example.train.controller;

import com.example.train.domain.Train;
import com.example.train.dto.CarDto;
import com.example.train.dto.SeatDto;
import com.example.train.dto.StationDto;
import com.example.train.dto.TrainDto;
import com.example.train.repository.CarRepository;
import com.example.train.repository.SeatRepository;
import com.example.train.repository.StationRepository;
import com.example.train.repository.TrainRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.List;

@RestController
@RequestMapping("/api")
@RequiredArgsConstructor
public class TrainController {

    private final TrainRepository trainRepository;
    private final StationRepository stationRepository;
    private final CarRepository carRepository;
    private final SeatRepository seatRepository;

    // 1) 역 목록: HomeScreen에서 출발/도착 선택용
    @GetMapping("/stations")
    public List<StationDto> getStations() {
        return stationRepository.findAll().stream()
                .map(s -> new StationDto(s.getId(), s.getName()))
                .toList();
    }

    // 2) 열차 검색: origin, dest, date(필수), after(선택)
    @GetMapping("/trains")
    public List<TrainDto> searchTrains(
            @RequestParam("origin") String originName,
            @RequestParam("dest") String destName,
            @RequestParam("date")
            @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate date,
            @RequestParam(value = "after", required = false)
            @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) LocalDateTime after
    ) {

        LocalDateTime start = date.atStartOfDay();
        LocalDateTime end = start.plusDays(1);

        if (after != null && after.isAfter(start)) {
            start = after; // 환승 2구간에서 사용
        }

        List<Train> trains = trainRepository.searchTrains(
                originName, destName, start, end
        );

        return trains.stream()
                .map(t -> TrainDto.builder()
                        .id(t.getId())
                        .trainNo(t.getTrainNo())
                        .trainType(t.getTrainType())
                        .origin(t.getOriginStation().getName())
                        .dest(t.getDestStation().getName())
                        .departureTime(t.getDepartureTime().toString())
                        .arrivalTime(t.getArrivalTime().toString())
                        .build())
                .toList();
    }

    // 3) 특정 열차의 호차 목록 (1~4호차)
    @GetMapping("/trains/{trainId}/cars")
    public List<CarDto> getCarsByTrain(@PathVariable Long trainId) {
        return carRepository.findByTrainIdOrderByCarNo(trainId).stream()
                .map(c -> new CarDto(c.getId(), c.getCarNo()))
                .toList();
    }

    // 4) 특정 호차의 좌석 목록
    @GetMapping("/cars/{carId}/seats")
    public List<SeatDto> getSeatsByCar(@PathVariable Long carId) {
        return seatRepository.findByCarIdOrderByRowNoAscColAsc(carId).stream()
                .map(s -> new SeatDto(
                        s.getId(),
                        s.getRowNo(),
                        s.getCol(),
                        s.getSeatCode(),
                        s.getStatus().name()
                ))
                .toList();
    }
}
