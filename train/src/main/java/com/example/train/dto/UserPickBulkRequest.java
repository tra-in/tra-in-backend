package com.example.train.dto;

import lombok.*;
import java.time.LocalDateTime;
import java.util.List;

@Getter @Setter
@NoArgsConstructor @AllArgsConstructor
public class UserPickBulkRequest {
    private Long userId;
    private Long userTicketId;
    private String destStation;
    private List<PickItem> picks;

    @Getter @Setter
    @NoArgsConstructor @AllArgsConstructor
    public static class PickItem {
        private String contentId;
        private String title;
        private String address;
        private Double distanceKm;
        private String contentTypeName;
        private Double latitude;
        private Double longitude;
        private String imageUrl;
        private String phone;
        private LocalDateTime startTime;
        private LocalDateTime endTime;
    }
}
