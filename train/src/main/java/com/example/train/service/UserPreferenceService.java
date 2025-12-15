package com.example.train.service;

import com.example.train.domain.TravelPreference;
import com.example.train.domain.UserPreference;
import com.example.train.dto.UserPreferenceRequestDto;
import com.example.train.repository.UserPreferenceRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;

@Service
@RequiredArgsConstructor
public class UserPreferenceService {

    private final UserPreferenceRepository userPreferenceRepository;

    @Transactional
    public void upsert(UserPreferenceRequestDto req) {
        if (req.getUserId() == null || req.getTicketId() == null) {
            throw new IllegalArgumentException("userId, ticketId는 필수입니다.");
        }
        if (req.getTravelPreference() == null || req.getTravelPreference().isBlank()) {
            throw new IllegalArgumentException("travelPreference는 필수입니다.");
        }

        // ✅ 문자열(한글) -> ENUM
        TravelPreference pref;
        try {
            pref = TravelPreference.from(req.getTravelPreference());
        } catch (Exception e) {
            throw new IllegalArgumentException("유효하지 않은 travelPreference 입니다: " + req.getTravelPreference());
        }

        UserPreference entity = userPreferenceRepository
                .findByUserIdAndTicketId(req.getUserId(), req.getTicketId())
                .orElseGet(() -> UserPreference.builder()
                        .userId(req.getUserId())
                        .ticketId(req.getTicketId())
                        .build()
                );

        entity.setTravelPreference(pref);
        entity.setUpdatedAt(LocalDateTime.now()); // ✅ 업데이트 시간 보장

        userPreferenceRepository.save(entity);
    }
}
