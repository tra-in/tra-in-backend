package com.example.train.dto;

import lombok.Data;
import java.util.List;

@Data
public class UserPickBulkRequest {

    private Long userId;
    private Long userTicketId;
    private String destStation;
    private List<PickDto> picks;

    @Data
    public static class PickDto {
        private Long contentId;
        private String title;
        private String address;
        private Double distanceKm;
        private String contentTypeName;
        private Double latitude;
        private Double longitude;
        private String imageUrl;
        private String phone;
    }
}
