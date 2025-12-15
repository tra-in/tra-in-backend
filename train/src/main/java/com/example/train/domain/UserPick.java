package com.example.train.domain;

import jakarta.persistence.*;
import lombok.*;

import java.time.LocalDateTime;

@Entity
@Table(
        name = "user_pick",
        uniqueConstraints = {
                @UniqueConstraint(
                        name = "uk_user_ticket_content",
                        columnNames = {"user_id", "ticket_id", "content_id"}
                )
        }
)
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class UserPick {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "user_id", nullable = false)
    private Long userId;

    @Column(name = "ticket_id", nullable = false)
    private Long ticketId;

    @Column(name = "dest_station", nullable = false)
    private String destStation;

    @Column(name = "content_id", nullable = false)
    private Long contentId;

    private String title;
    private String address;
    private Double distanceKm;
    private String contentTypeName;
    private Double latitude;
    private Double longitude;
    private String imageUrl;
    private String phone;

    /** ❤️ 고정 여부 */
    @Column(name = "is_pinned", nullable = false)
    private boolean pinned;

    /** ❌ 재추천 제외 여부 */
    @Column(name = "is_excluded", nullable = false)
    private boolean excluded;

    @Column(name = "created_at", nullable = false)
    private LocalDateTime createdAt;

    @Column(name = "updated_at", nullable = false)
    private LocalDateTime updatedAt;

    @PrePersist
    void onCreate() {
        createdAt = updatedAt = LocalDateTime.now();
    }

    @PreUpdate
    void onUpdate() {
        updatedAt = LocalDateTime.now();
    }
}
