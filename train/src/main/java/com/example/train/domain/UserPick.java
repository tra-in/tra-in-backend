package com.example.train.domain;
import jakarta.persistence.*;
import lombok.*;
import java.time.LocalDateTime;

@Entity @Table( name = "user_pick",
        uniqueConstraints = { @UniqueConstraint(
                name = "uq_pick_once",
                columnNames = {"user_ticket_id", "content_id"}) } )
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class UserPick {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    @Column(name="user_id", nullable=false)
    private Long userId;
    @Column(name="user_ticket_id", nullable=false)
    private Long userTicketId;
    @Column(name="dest_station", nullable=false, length=50)
    private String destStation;
    @Column(name="content_id", nullable=false, length=50)
    private String contentId;
    @Column(name="title", nullable=false, length=255)
    private String title;
    @Column(name="address")
    private String address;
    @Column(name="distance_km")
    private Double distanceKm;
    @Column(name="content_type_name", length=50)
    private String contentTypeName;
    @Column(name="latitude")
    private Double latitude;
    @Column(name="longitude")
    private Double longitude;
    @Column(name="image_url", length=500)
    private String imageUrl;
    @Column(name="phone", length=50)
    private String phone;
    @Column(name="start_time")
    private LocalDateTime startTime;
    @Column(name="end_time")
    private LocalDateTime endTime;
}