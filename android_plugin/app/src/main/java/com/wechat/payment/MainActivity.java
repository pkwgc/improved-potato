package com.wechat.payment;

import androidx.appcompat.app.AppCompatActivity;

import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.util.Log;
import android.view.View;
import android.widget.Button;
import android.widget.TextView;
import android.widget.Toast;

import java.net.URLDecoder;
import java.util.HashMap;
import java.util.Map;

public class MainActivity extends AppCompatActivity {
    private static final String TAG = "MainActivity";
    
    private TextView statusText;
    private Button testButton;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);
        
        initViews();
        handleIntent(getIntent());
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        handleIntent(intent);
    }

    private void initViews() {
        statusText = findViewById(R.id.statusText);
        testButton = findViewById(R.id.testButton);
        
        testButton.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                testWithSampleData();
            }
        });
        
        updateStatus("WeChat Payment Plugin Ready");
    }

    private void handleIntent(Intent intent) {
        if (intent == null) {
            return;
        }

        String action = intent.getAction();
        Uri data = intent.getData();

        Log.d(TAG, "Handling intent - Action: " + action + ", Data: " + data);

        if (Intent.ACTION_VIEW.equals(action) && data != null) {
            handleSchemeIntent(data);
        }
    }

    private void handleSchemeIntent(Uri data) {
        try {
            String scheme = data.getScheme();
            Log.d(TAG, "Received scheme: " + scheme + ", URI: " + data.toString());
            
            if ("wechatpay".equals(scheme) || "wxpay".equals(scheme)) {
                PaymentParams params = extractPaymentParams(data);
                if (params != null && params.isValid()) {
                    updateStatus("Processing payment...");
                    boolean success = PaymentHandler.processPayment(this, params);
                    if (success) {
                        updateStatus("Payment request sent to WeChat");
                    } else {
                        updateStatus("Failed to process payment");
                    }
                } else {
                    updateStatus("Invalid payment parameters");
                    Toast.makeText(this, "支付参数无效", Toast.LENGTH_SHORT).show();
                }
            } else {
                updateStatus("Unsupported scheme: " + scheme);
            }
        } catch (Exception e) {
            Log.e(TAG, "Error handling scheme intent", e);
            updateStatus("Error: " + e.getMessage());
            Toast.makeText(this, "处理支付请求时出错", Toast.LENGTH_SHORT).show();
        }
    }

    private PaymentParams extractPaymentParams(Uri data) {
        try {
            Map<String, String> params = parseQueryParameters(data.getQuery());
            
            PaymentParams paymentParams = new PaymentParams();
            paymentParams.prepayId = params.get("prepayId");
            paymentParams.appId = params.get("appId");
            paymentParams.partnerId = params.get("partnerId");
            paymentParams.nonceStr = params.get("nonceStr");
            paymentParams.sign = params.get("sign");
            paymentParams.spreadField = params.get("spreadField");
            paymentParams.timestamp = params.get("timestamp");

            Log.d(TAG, "Extracted payment params: " + paymentParams.toString());
            return paymentParams;
            
        } catch (Exception e) {
            Log.e(TAG, "Error extracting payment parameters", e);
            return null;
        }
    }

    private Map<String, String> parseQueryParameters(String query) {
        Map<String, String> params = new HashMap<>();
        if (query != null && !query.isEmpty()) {
            String[] pairs = query.split("&");
            for (String pair : pairs) {
                String[] keyValue = pair.split("=", 2);
                if (keyValue.length == 2) {
                    try {
                        String key = URLDecoder.decode(keyValue[0], "UTF-8");
                        String value = URLDecoder.decode(keyValue[1], "UTF-8");
                        params.put(key, value);
                    } catch (Exception e) {
                        Log.w(TAG, "Error decoding parameter: " + pair, e);
                    }
                }
            }
        }
        return params;
    }

    private void testWithSampleData() {
        PaymentParams params = new PaymentParams(
            "wx19162432174915e15d5011fb071e330000", // prepayId
            "wxdf261c3b90ffbc25",                    // appId
            "1236537302",                           // partnerId
            "tUQgTXocIAFakmHNEWGGDCtaXIQxKsOc",     // nonceStr
            "82B29937ECE7A47F45409BD85B84C951",     // sign
            "Sign=WXPay",                           // spreadField
            "1758270368"                            // timestamp
        );

        updateStatus("Testing with sample data...");
        boolean success = PaymentHandler.processPayment(this, params);
        if (success) {
            updateStatus("Test payment request sent");
        } else {
            updateStatus("Test payment failed");
        }
    }

    private void updateStatus(String message) {
        if (statusText != null) {
            statusText.setText(message);
        }
        Log.i(TAG, "Status: " + message);
    }
}
