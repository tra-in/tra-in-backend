package com.example.train.controller;

import com.example.train.dto.UserPreferenceRequestDto;
import com.example.train.service.UserPreferenceService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api")
@RequiredArgsConstructor
@CrossOrigin(origins = "*")
public class UserPreferenceController {

    private final UserPreferenceService userPreferenceService;

    // ✅ POST /api/user-preferences
    @PostMapping("/user-preferences")
    public ResponseEntity<Void> save(@RequestBody UserPreferenceRequestDto req) {
        userPreferenceService.upsert(req);
        return ResponseEntity.ok().build();
    }
}
