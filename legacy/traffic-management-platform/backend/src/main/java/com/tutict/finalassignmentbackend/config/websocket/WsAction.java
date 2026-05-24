package com.tutict.finalassignmentbackend.config.websocket;

import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;

@Retention(RetentionPolicy.RUNTIME)
@Target(ElementType.METHOD)
public @interface WsAction {

    String service();

    String action();

    boolean exposed() default false;

    boolean allowAnonymous() default false;

    String[] rolesAllowed() default {};
}
