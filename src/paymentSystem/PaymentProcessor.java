package paymentSystem;

public interface PaymentProcessor {

    public void pay(double amount);

    default void printReciepts(double amount){
        System.out.println("Receipt printed. and payment of "+ amount + " processed successfully.");
    }

    public static void supportedPaymentMethods() {
        System.out.println("Supported payment methods: Credit Card, Debit Card, PayPal, Bank Transfer.");
    }   


    
}
