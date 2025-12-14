package com.example.train.controller;

import com.example.train.dto.UserTicketDto;
import com.example.train.service.UserTicketService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api")
@RequiredArgsConstructor
@CrossOrigin(origins = "*")   // 필요시 CORS 허용
public class UserTicketController {

    private final UserTicketService userTicketService;

    /**
     * 예매 내역 저장
     * POST /api/user-tickets
     */
    @PostMapping("/user-tickets")
    public ResponseEntity<Void> createTickets(@RequestBody UserTicketDto request) {
        userTicketService.createTickets(request);
        return ResponseEntity.ok().build();
    }
}
