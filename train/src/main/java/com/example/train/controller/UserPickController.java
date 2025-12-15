package com.example.train.controller;

import com.example.train.dto.UserPickBulkRequest;
import com.example.train.dto.UserPickRefreshRequest;
import com.example.train.service.UserPickService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/user-picks")
@RequiredArgsConstructor
@CrossOrigin(origins = "*")
public class UserPickController {

    private final UserPickService service;

    /** 추천 결과 저장 */
    @PostMapping("/bulk")
    public ResponseEntity<Void> saveBulk(@RequestBody UserPickBulkRequest req) {
        service.saveBulk(req);
        return ResponseEntity.ok().build();
    }

    /** 새로고침 cleanup */
    @PostMapping("/refresh-cleanup")
    public ResponseEntity<Void> refreshCleanup(@RequestBody UserPickRefreshRequest req) {
        service.refreshCleanup(req);
        return ResponseEntity.ok().build();
    }

    /** ❌ 제외 목록 */
    @GetMapping("/excluded")
    public ResponseEntity<Map<String, List<Long>>> getExcluded(
            @RequestParam Long userId,
            @RequestParam Long userTicketId
    ) {
        List<Long> ids = service.getExcludedContentIds(userId, userTicketId);
        return ResponseEntity.ok(Map.of("excludedContentIds", ids));
    }
}
