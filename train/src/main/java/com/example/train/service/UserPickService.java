package com.example.train.service;

import com.example.train.domain.UserPick;
import com.example.train.dto.UserPickBulkRequest;
import com.example.train.dto.UserPickRefreshRequest;
import com.example.train.repository.UserPickRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Service
@RequiredArgsConstructor
public class UserPickService {

    private final UserPickRepository repository;

    /** 추천 결과 bulk 저장 */
    @Transactional
    public void saveBulk(UserPickBulkRequest req) {

        if (req.getUserId() == null || req.getUserTicketId() == null || req.getDestStation() == null) {
            throw new IllegalArgumentException("userId/userTicketId/destStation은 필수입니다.");
        }

        for (UserPickBulkRequest.PickDto p : req.getPicks()) {
            repository.findByUserIdAndTicketIdAndContentId(
                    req.getUserId(), req.getUserTicketId(), p.getContentId()
            ).ifPresentOrElse(
                    exist -> {
                        // 이미 있으면 skip (또는 업데이트)
                    },
                    () -> {
                        repository.save(
                                UserPick.builder()
                                        .userId(req.getUserId())
                                        .ticketId(req.getUserTicketId())
                                        .destStation(req.getDestStation())
                                        .contentId(p.getContentId())
                                        .title(p.getTitle())
                                        .address(p.getAddress())
                                        .distanceKm(p.getDistanceKm())
                                        .contentTypeName(p.getContentTypeName())
                                        .latitude(p.getLatitude())
                                        .longitude(p.getLongitude())
                                        .imageUrl(p.getImageUrl())
                                        .phone(p.getPhone())
                                        .pinned(false)
                                        .excluded(false)
                                        .build()
                        );
                    }
            );
        }
    }

    /** ❤️ 고정 유지 + ❌ 제거/제외 */
    @Transactional
    public void refreshCleanup(UserPickRefreshRequest req) {

        if (req.getUserId() == null || req.getUserTicketId() == null) {
            throw new IllegalArgumentException("userId/userTicketId는 필수입니다.");
        }

        // ❌ 제거 + 제외 처리
        if (req.getRemoveContentIds() != null) {
            for (Long contentId : req.getRemoveContentIds()) {
                repository.findByUserIdAndTicketIdAndContentId(
                        req.getUserId(), req.getUserTicketId(), contentId
                ).ifPresent(pick -> {
                    pick.setExcluded(true);
                    pick.setPinned(false);
                });
            }
        }

        // ❤️ 고정 유지
        if (req.getKeepContentIds() != null) {
            for (Long contentId : req.getKeepContentIds()) {
                repository.findByUserIdAndTicketIdAndContentId(
                        req.getUserId(), req.getUserTicketId(), contentId
                ).ifPresent(pick -> pick.setPinned(true));
            }
        }
    }

    /** ❌ 제외된 contentId 목록 */
    @Transactional(readOnly = true)
    public List<Long> getExcludedContentIds(Long userId, Long ticketId) {
        return repository.findByUserIdAndTicketIdAndExcludedTrue(userId, ticketId)
                .stream()
                .map(UserPick::getContentId)
                .toList();
    }
}
