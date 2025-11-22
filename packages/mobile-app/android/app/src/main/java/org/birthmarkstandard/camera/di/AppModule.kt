package org.birthmarkstandard.camera.di

import android.content.Context
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import org.birthmarkstandard.camera.services.CryptoService
import org.birthmarkstandard.camera.services.KeystoreService
import org.birthmarkstandard.camera.services.NetworkService
import org.birthmarkstandard.camera.services.SubmissionRepository
import javax.inject.Singleton

/**
 * Hilt dependency injection module for app-wide singletons.
 */
@Module
@InstallIn(SingletonComponent::class)
object AppModule {

    @Provides
    @Singleton
    fun provideCryptoService(): CryptoService {
        return CryptoService()
    }

    @Provides
    @Singleton
    fun provideKeystoreService(
        @ApplicationContext context: Context,
        cryptoService: CryptoService
    ): KeystoreService {
        return KeystoreService(context, cryptoService)
    }

    @Provides
    @Singleton
    fun provideNetworkService(): NetworkService {
        return NetworkService()
    }

    @Provides
    @Singleton
    fun provideSubmissionRepository(
        @ApplicationContext context: Context
    ): SubmissionRepository {
        return SubmissionRepository(context)
    }
}
