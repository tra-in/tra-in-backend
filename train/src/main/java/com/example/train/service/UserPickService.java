package com.example.train.service;

import com.example.train.dto.UserPickBulkRequest;
import com.example.train.domain.UserPick;
import com.example.train.repository.UserPickRepository;
import lombok.*;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.*;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class UserPickService {

    private final UserPickRepository userPickRepository;

    @Transactional
    public BulkSaveResult saveBulk(UserPickBulkRequest req) {
        if (req.getUserId() == null || req.getUserTicketId() == null || req.getDestStation() == null) {
            throw new IllegalArgumentException("userId/userTicketId/destStation은 필수입니다.");
        }
        if (req.getPicks() == null || req.getPicks().isEmpty()) {
            return new BulkSaveResult(0, 0);
        }

        // 1) 요청 contentId 목록
        List<String> contentIds = req.getPicks().stream()
                .map(UserPickBulkRequest.PickItem::getContentId)
                .filter(Objects::nonNull)
                .distinct()
                .toList();

        // 2) 기존 저장된 것 미리 조회 → 중복 스킵
        Set<String> exists = userPickRepository
                .findByUserTicketIdAndContentIdIn(req.getUserTicketId(), contentIds)
                .stream()
                .map(UserPick::getContentId)
                .collect(Collectors.toSet());

        // 3) 저장할 것만 엔티티로 변환
        List<UserPick> toSave = new ArrayList<>();
        for (UserPickBulkRequest.PickItem p : req.getPicks()) {
            if (p.getContentId() == null) continue;
            if (exists.contains(p.getContentId())) continue;

            toSave.add(UserPick.builder()
                    .userId(req.getUserId())
                    .userTicketId(req.getUserTicketId())
                    .destStation(req.getDestStation())
                    .contentId(p.getContentId())
                    .title(nvl(p.getTitle(), "추천 장소"))
                    .address(p.getAddress())
                    .distanceKm(p.getDistanceKm())
                    .contentTypeName(p.getContentTypeName())
                    .latitude(p.getLatitude())
                    .longitude(p.getLongitude())
                    .imageUrl(p.getImageUrl())
                    .phone(p.getPhone())
                    .startTime(p.getStartTime())
                    .endTime(p.getEndTime())
                    .build());
        }

        userPickRepository.saveAll(toSave);
        return new BulkSaveResult(toSave.size(), exists.size());
    }

    private String nvl(String s, String def) {
        return (s == null || s.isBlank()) ? def : s;
    }

    @Getter @AllArgsConstructor
    public static class BulkSaveResult {
        private int savedCount;
        private int skippedAsDuplicateCount;
    }
}
