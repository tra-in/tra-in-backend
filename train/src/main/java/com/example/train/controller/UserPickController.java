package com.example.train.controller;

import com.example.train.dto.UserPickBulkRequest;
import com.example.train.service.UserPickService;
import lombok.*;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1/user-picks")
@RequiredArgsConstructor
public class UserPickController {

    private final UserPickService userPickService;

    @PostMapping("/bulk")
    public ResponseEntity<?> saveBulk(@RequestBody UserPickBulkRequest req) {
        var result = userPickService.saveBulk(req);
        return ResponseEntity.ok(result);
    }
}
